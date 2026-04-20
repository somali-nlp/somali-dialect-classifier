from somali_dialect_classifier.orchestration.flows import _run_locked_pipeline_task


class FakeLedger:
    def __init__(self):
        self.locked = False
        self.actions = []

    def is_source_locked(self, source):
        self.actions.append(("is_locked", source))
        return self.locked

    def acquire_source_lock(self, source, timeout=30):
        self.actions.append(("acquire", source, timeout))

    def release_source_lock(self, source):
        self.actions.append(("release", source))

    def register_pipeline_run(self, **kwargs):
        self.actions.append(("register", kwargs))

    def update_pipeline_run(self, **kwargs):
        self.actions.append(("update", kwargs))

    def get_statistics(self, source):
        self.actions.append(("stats", source))
        return {"by_state": {"processed": 42}}


class FakeProcessor:
    def __init__(
        self, run_id="20260313_120000_bbc_deadbeef", result_path="data/out.parquet", fail=False
    ):
        self.run_id = run_id
        self.result_path = result_path
        self.fail = fail

    def run(self):
        if self.fail:
            raise RuntimeError("processor boom")
        return self.result_path


def test_run_locked_pipeline_task_registers_processor_run_id_and_completes():
    ledger = FakeLedger()
    processor = FakeProcessor()

    result = _run_locked_pipeline_task(
        processor_name="bbc",
        display_source="BBC",
        pipeline_type="web",
        processor_kwargs={"force": False},
        include_statistics=True,
        start_message="Starting BBC pipeline...",
        ledger_factory=lambda: ledger,
        processor_factory=lambda name, **kwargs: processor,
        source_name_factory=lambda name, **kwargs: "BBC-Somali",
        git_commit_resolver=lambda: "abc123",
        config_snapshot={"quota": 100},
    )

    assert result["status"] == "success"
    assert result["silver_path"] == "data/out.parquet"
    assert result["statistics"]["by_state"]["processed"] == 42

    register_call = next(action for action in ledger.actions if action[0] == "register")
    assert register_call[1]["run_id"] == processor.run_id
    assert register_call[1]["pipeline_type"] == "web"

    updates = [action[1] for action in ledger.actions if action[0] == "update"]
    assert updates[0]["status"] == "RUNNING"
    assert updates[-1]["status"] == "COMPLETED"
    assert updates[-1]["records_processed"] == 42
    assert ledger.actions[-1] == ("release", "bbc")


def test_run_locked_pipeline_task_marks_registered_run_failed():
    ledger = FakeLedger()
    processor = FakeProcessor(fail=True)

    result = _run_locked_pipeline_task(
        processor_name="huggingface",
        display_source="HuggingFace",
        pipeline_type="stream",
        processor_kwargs={"force": False},
        start_message="Starting HuggingFace pipeline...",
        ledger_factory=lambda: ledger,
        processor_factory=lambda name, **kwargs: processor,
        source_name_factory=lambda name, **kwargs: "HuggingFace-Somali_c4",
        git_commit_resolver=lambda: "abc123",
        config_snapshot={"quota": 200},
    )

    assert result["status"] == "failed"
    register_call = next(action for action in ledger.actions if action[0] == "register")
    assert register_call[1]["run_id"] == processor.run_id

    updates = [action[1] for action in ledger.actions if action[0] == "update"]
    assert updates[0]["status"] == "RUNNING"
    assert updates[-1]["status"] == "FAILED"
    assert "processor boom" in updates[-1]["errors"]
    assert ledger.actions[-1] == ("release", "huggingface")

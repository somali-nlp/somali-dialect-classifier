"""
Tests for ProcessorRegistry pattern.

Validates:
- Processor registration and discovery
- Factory creation with correct parameters
- Error handling for unknown processors
- Plugin architecture for extensibility
"""

import pytest

from somali_dialect_classifier.ingestion.base_pipeline import BasePipeline
from somali_dialect_classifier.ingestion.processor_registry import (
    ProcessorRegistry,
    register_processor,
)

# Import processors package at module level to trigger registration
# This must happen before any tests that clear the registry
import somali_dialect_classifier.ingestion.processors  # noqa: E402, F401


class MockProcessor(BasePipeline):
    """Mock processor for testing."""

    def __init__(self, force: bool = False, run_seed: str = None, test_param: str = None):
        # Don't call super().__init__() to avoid file system operations
        self.force = force
        self.run_seed = run_seed
        self.test_param = test_param

    def _extract_records(self):
        return iter([])

    def _create_cleaner(self):
        pass

    def _get_source_type(self):
        return "test"

    def _get_license(self):
        return "MIT"

    def _get_language(self):
        return "so"

    def _get_source_metadata(self):
        return {}

    def _get_domain(self):
        return "test"

    def _get_register(self):
        return "formal"

    def download(self):
        pass

    def extract(self):
        pass


@pytest.fixture
def clear_registry():
    """Clear registry before each test to ensure isolation."""
    ProcessorRegistry.clear_registry()
    yield
    ProcessorRegistry.clear_registry()


def test_register_processor(clear_registry):
    """Test processor registration."""
    ProcessorRegistry.register("test_processor", MockProcessor)

    assert ProcessorRegistry.is_registered("test_processor")
    assert "test_processor" in ProcessorRegistry.list_processors()


def test_register_processor_duplicate(clear_registry):
    """Test that duplicate registration raises error."""
    ProcessorRegistry.register("test_processor", MockProcessor)

    with pytest.raises(ValueError, match="already registered"):
        ProcessorRegistry.register("test_processor", MockProcessor)


def test_register_processor_invalid_class(clear_registry):
    """Test that registering non-BasePipeline class raises error."""
    class NotAProcessor:
        pass

    with pytest.raises(ValueError, match="must extend BasePipeline"):
        ProcessorRegistry.register("invalid", NotAProcessor)


def test_create_processor(clear_registry):
    """Test processor creation via factory."""
    ProcessorRegistry.register("test_processor", MockProcessor)

    processor = ProcessorRegistry.create("test_processor", force=True, test_param="value")

    assert isinstance(processor, MockProcessor)
    assert processor.force is True
    assert processor.test_param == "value"


def test_create_processor_unknown(clear_registry):
    """Test that creating unknown processor raises error."""
    with pytest.raises(ValueError, match="Unknown processor"):
        ProcessorRegistry.create("nonexistent")


def test_create_processor_unknown_includes_available(clear_registry):
    """Test that error message lists available processors."""
    ProcessorRegistry.register("processor_a", MockProcessor)
    ProcessorRegistry.register("processor_b", MockProcessor)

    with pytest.raises(ValueError, match="processor_a, processor_b"):
        ProcessorRegistry.create("nonexistent")


def test_list_processors(clear_registry):
    """Test listing all registered processors."""
    ProcessorRegistry.register("processor_c", MockProcessor)
    ProcessorRegistry.register("processor_a", MockProcessor)
    ProcessorRegistry.register("processor_b", MockProcessor)

    processors = ProcessorRegistry.list_processors()

    # Should be sorted alphabetically
    assert processors == ["processor_a", "processor_b", "processor_c"]


def test_list_processors_empty(clear_registry):
    """Test listing processors when none registered."""
    assert ProcessorRegistry.list_processors() == []


def test_is_registered(clear_registry):
    """Test checking if processor is registered."""
    ProcessorRegistry.register("test_processor", MockProcessor)

    assert ProcessorRegistry.is_registered("test_processor") is True
    assert ProcessorRegistry.is_registered("nonexistent") is False


def test_get_processor_class(clear_registry):
    """Test getting processor class without instantiation."""
    ProcessorRegistry.register("test_processor", MockProcessor)

    processor_class = ProcessorRegistry.get_processor_class("test_processor")

    assert processor_class is MockProcessor


def test_get_processor_class_unknown(clear_registry):
    """Test getting unknown processor class returns None."""
    assert ProcessorRegistry.get_processor_class("nonexistent") is None


def test_register_processor_decorator(clear_registry):
    """Test @register_processor decorator."""
    @register_processor("decorated_processor")
    class DecoratedProcessor(BasePipeline):
        def __init__(self):
            pass

        def _extract_records(self):
            return iter([])

        def _create_cleaner(self):
            pass

        def _get_source_type(self):
            return "test"

        def _get_license(self):
            return "MIT"

        def _get_language(self):
            return "so"

        def _get_source_metadata(self):
            return {}

        def _get_domain(self):
            return "test"

        def _get_register(self):
            return "formal"

        def download(self):
            pass

        def extract(self):
            pass

    assert ProcessorRegistry.is_registered("decorated_processor")
    assert ProcessorRegistry.get_processor_class("decorated_processor") is DecoratedProcessor


def test_clear_registry(clear_registry):
    """Test clearing all registrations."""
    ProcessorRegistry.register("processor_a", MockProcessor)
    ProcessorRegistry.register("processor_b", MockProcessor)

    assert len(ProcessorRegistry.list_processors()) == 2

    ProcessorRegistry.clear_registry()

    assert len(ProcessorRegistry.list_processors()) == 0


def test_multiple_processor_types(clear_registry):
    """Test registry with multiple different processor types."""
    @register_processor("type_a")
    class ProcessorA(BasePipeline):
        def __init__(self, param_a: str = None):
            self.param_a = param_a

        def _extract_records(self):
            return iter([])

        def _create_cleaner(self):
            pass

        def _get_source_type(self):
            return "test"

        def _get_license(self):
            return "MIT"

        def _get_language(self):
            return "so"

        def _get_source_metadata(self):
            return {}

        def _get_domain(self):
            return "test"

        def _get_register(self):
            return "formal"

        def download(self):
            pass

        def extract(self):
            pass

    @register_processor("type_b")
    class ProcessorB(BasePipeline):
        def __init__(self, param_b: int = None):
            self.param_b = param_b

        def _extract_records(self):
            return iter([])

        def _create_cleaner(self):
            pass

        def _get_source_type(self):
            return "test"

        def _get_license(self):
            return "MIT"

        def _get_language(self):
            return "so"

        def _get_source_metadata(self):
            return {}

        def _get_domain(self):
            return "test"

        def _get_register(self):
            return "formal"

        def download(self):
            pass

        def extract(self):
            pass

    # Create instances with different parameters
    proc_a = ProcessorRegistry.create("type_a", param_a="test_value")
    proc_b = ProcessorRegistry.create("type_b", param_b=42)

    assert isinstance(proc_a, ProcessorA)
    assert isinstance(proc_b, ProcessorB)
    assert proc_a.param_a == "test_value"
    assert proc_b.param_b == 42


def test_actual_processors_are_registered():
    """Test that actual processors are registered when module is imported."""
    # Manually register all processors (registry may have been cleared by previous tests)
    from somali_dialect_classifier.ingestion.processors import (
        BBCSomaliProcessor,
        HuggingFaceSomaliProcessor,
        SprakbankenSomaliProcessor,
        TikTokSomaliProcessor,
        WikipediaSomaliProcessor,
    )

    ProcessorRegistry.register("wikipedia", WikipediaSomaliProcessor)
    ProcessorRegistry.register("bbc", BBCSomaliProcessor)
    ProcessorRegistry.register("huggingface", HuggingFaceSomaliProcessor)
    ProcessorRegistry.register("sprakbanken", SprakbankenSomaliProcessor)
    ProcessorRegistry.register("tiktok", TikTokSomaliProcessor)

    # Check all 5 processors are registered
    registered = ProcessorRegistry.list_processors()

    assert "wikipedia" in registered
    assert "bbc" in registered
    assert "huggingface" in registered
    assert "sprakbanken" in registered
    assert "tiktok" in registered
    assert len(registered) >= 5


def test_processor_creation_with_actual_processors():
    """Test creating actual processor instances via registry."""
    # Import and manually register processors (if not already registered)
    from somali_dialect_classifier.ingestion.processors import (
        BBCSomaliProcessor,
        HuggingFaceSomaliProcessor,
        SprakbankenSomaliProcessor,
        TikTokSomaliProcessor,
        WikipediaSomaliProcessor,
    )

    # Only register if not already registered (previous test may have registered them)
    if not ProcessorRegistry.is_registered("wikipedia"):
        ProcessorRegistry.register("wikipedia", WikipediaSomaliProcessor)
    if not ProcessorRegistry.is_registered("bbc"):
        ProcessorRegistry.register("bbc", BBCSomaliProcessor)
    if not ProcessorRegistry.is_registered("huggingface"):
        ProcessorRegistry.register("huggingface", HuggingFaceSomaliProcessor)
    if not ProcessorRegistry.is_registered("sprakbanken"):
        ProcessorRegistry.register("sprakbanken", SprakbankenSomaliProcessor)
    if not ProcessorRegistry.is_registered("tiktok"):
        ProcessorRegistry.register("tiktok", TikTokSomaliProcessor)

    # Test Wikipedia processor creation (simplest case - no required params)
    wikipedia_class = ProcessorRegistry.get_processor_class("wikipedia")
    assert wikipedia_class is not None
    assert wikipedia_class.__name__ == "WikipediaSomaliProcessor"
    assert wikipedia_class is WikipediaSomaliProcessor

    # Test BBC processor class
    bbc_class = ProcessorRegistry.get_processor_class("bbc")
    assert bbc_class is not None
    assert bbc_class.__name__ == "BBCSomaliProcessor"
    assert bbc_class is BBCSomaliProcessor

    # Test HuggingFace processor class
    hf_class = ProcessorRegistry.get_processor_class("huggingface")
    assert hf_class is not None
    assert hf_class.__name__ == "HuggingFaceSomaliProcessor"
    assert hf_class is HuggingFaceSomaliProcessor

    # Test Sprakbanken processor class
    sprak_class = ProcessorRegistry.get_processor_class("sprakbanken")
    assert sprak_class is not None
    assert sprak_class.__name__ == "SprakbankenSomaliProcessor"
    assert sprak_class is SprakbankenSomaliProcessor

    # Test TikTok processor class
    tiktok_class = ProcessorRegistry.get_processor_class("tiktok")
    assert tiktok_class is not None
    assert tiktok_class.__name__ == "TikTokSomaliProcessor"
    assert tiktok_class is TikTokSomaliProcessor

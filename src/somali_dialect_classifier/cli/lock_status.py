#!/usr/bin/env python3
"""
CLI tool to check lock status for all sources.

Usage:
    python -m somali_dialect_classifier.cli.lock_status
    python -m somali_dialect_classifier.cli.lock_status --cleanup
"""
from datetime import datetime
from pathlib import Path

import click

from ..preprocessing.crawl_ledger import LockManager


@click.command()
@click.option("--lock-dir", default=".locks", help="Lock directory path")
@click.option("--cleanup", is_flag=True, help="Remove stale locks (>24h old)")
def lock_status(lock_dir: str, cleanup: bool):
    """Check lock status for all sources."""
    lock_manager = LockManager(Path(lock_dir))

    sources = ["wikipedia", "bbc", "sprakbanken", "tiktok", "huggingface"]

    click.echo("=" * 60)
    click.echo("Pipeline Lock Status")
    click.echo("=" * 60)
    click.echo()

    locked_count = 0
    for source in sources:
        is_locked = lock_manager.is_locked(source)
        status = "LOCKED" if is_locked else "Available"
        status_symbol = "🔒" if is_locked else "✓"

        click.echo(f"{source:15s} {status_symbol} {status}")

        if is_locked:
            locked_count += 1
            # Show lock file age if locked
            lock_file = lock_manager.lock_dir / f"{source}.lock"
            if lock_file.exists():
                age_minutes = (datetime.now().timestamp() - lock_file.stat().st_mtime) / 60
                if age_minutes < 60:
                    click.echo(f"                (lock age: {age_minutes:.1f} minutes)")
                else:
                    age_hours = age_minutes / 60
                    click.echo(f"                (lock age: {age_hours:.1f} hours)")

    click.echo()
    click.echo("-" * 60)
    if locked_count > 0:
        click.echo(f"Status: {locked_count} pipeline(s) currently running")
    else:
        click.echo("Status: All pipelines available (no active runs)")
    click.echo("-" * 60)

    if cleanup:
        click.echo()
        click.echo("Cleaning up stale locks (>24h old)...")
        lock_manager.cleanup_stale_locks(max_age_hours=24)
        click.echo("Cleanup complete.")


if __name__ == "__main__":
    lock_status()

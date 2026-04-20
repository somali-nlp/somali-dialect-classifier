#!/usr/bin/env python3
"""Move silver metadata sidecars out of parquet partition directories."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move *_silver_metadata.json files into silver/_metadata/source=*/date_accessed=*."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("data/processed/silver"),
        help="Base silver directory to migrate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without changing files.",
    )
    return parser.parse_args()


def iter_legacy_sidecars(base_dir: Path) -> list[Path]:
    pattern = "source=*/date_accessed=*/*_silver_metadata.json"
    return sorted(path for path in base_dir.glob(pattern) if path.is_file())


def destination_for(base_dir: Path, sidecar_path: Path) -> Path:
    relative_parent = sidecar_path.relative_to(base_dir).parent
    return base_dir / "_metadata" / relative_parent / sidecar_path.name


def migrate_sidecars(base_dir: Path, dry_run: bool = False) -> int:
    moved = 0
    for sidecar_path in iter_legacy_sidecars(base_dir):
        destination = destination_for(base_dir, sidecar_path)
        if destination == sidecar_path:
            continue

        print(f"{sidecar_path} -> {destination}")
        if dry_run:
            moved += 1
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(sidecar_path.read_bytes())
        sidecar_path.unlink()
        moved += 1

    return moved


def main() -> int:
    args = parse_args()
    base_dir = args.base_dir

    if not base_dir.exists():
        print(f"Base directory not found: {base_dir}")
        return 1

    moved = migrate_sidecars(base_dir=base_dir, dry_run=args.dry_run)
    mode = "would move" if args.dry_run else "moved"
    print(f"{mode} {moved} sidecar file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
DEPRECATED: Use `somali-tools metrics consolidate` instead.

This script stub is maintained for backward compatibility.
Will be removed in Stage 2.

Legacy wrapper that calls the unified somali-tools CLI.

Usage:
    python scripts/generate_consolidated_metrics.py

Recommended:
    somali-tools metrics consolidate
"""

import sys
import warnings
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

warnings.warn(
    "scripts/generate_consolidated_metrics.py is deprecated. "
    "Use: somali-tools metrics consolidate",
    DeprecationWarning,
    stacklevel=2
)

print("\n⚠ DEPRECATION WARNING:")
print("  This script is deprecated and will be removed in Stage 2.")
print("  Please use: somali-tools metrics consolidate")
print("  Falling back to CLI...\n")

try:
    from somali_dialect_classifier.tools.cli import cli

    # Rewrite argv to call CLI command
    sys.argv = ['somali-tools', 'metrics', 'consolidate']

    # Call CLI
    cli(obj={})

except ImportError as e:
    print(f"\nError: Could not import CLI: {e}", file=sys.stderr)
    print("Install with: pip install -e .", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"\nError: {e}", file=sys.stderr)
    sys.exit(1)

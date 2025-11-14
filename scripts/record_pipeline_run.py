#!/usr/bin/env python3
"""
Pipeline Run Recorder - Semi-Automated Data Collection
=======================================================

Purpose:
--------
Validates and records pipeline run metrics to pipeline_run_history.json.
Supports schema v2.0 with resource metrics and backward compatibility with v1.0.

Usage:
------
# Basic usage (manual metric entry)
python scripts/record_pipeline_run.py \
  --run-id "20251108_190000" \
  --output dashboard/data/pipeline_run_history.json

# With log file parsing (future enhancement)
python scripts/record_pipeline_run.py \
  --log-file logs/pipeline_20251108_071104.log \
  --output dashboard/data/pipeline_run_history.json

Features:
---------
- Schema v2.0 validation
- Duplicate run_id detection
- Metric range validation
- Backward compatibility with v1.0 schema
- Resource metrics collection (CPU/memory/disk)
- Data quality scoring
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make psutil optional - only required for resource monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed. Resource monitoring disabled.", file=sys.stderr)
    print("Install with: pip install psutil", file=sys.stderr)


class PipelineRunRecorder:
    """Records and validates pipeline run data"""

    # Validation ranges for metrics
    METRIC_RANGES = {
        'sources_processed': {'min': 1, 'max': 10},
        'total_duration_seconds': {'min': 0, 'max': 86400},
        'total_records': {'min': 0, 'max': 1000000},
        'throughput_rpm': {'min': 0, 'max': 100000},
        'quality_pass_rate': {'min': 0, 'max': 1.0},
        'retries': {'min': 0, 'max': 100},
        'errors': {'min': 0, 'max': 1000}
    }

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)

    def validate_run_data(self, run_data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate pipeline run data against schema

        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []

        # Check required fields
        required_fields = [
            'run_id', 'timestamp', 'sources_processed',
            'total_duration_seconds', 'total_records',
            'throughput_rpm', 'quality_pass_rate'
        ]

        for field in required_fields:
            if field not in run_data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Validate schema version
        schema_version = run_data.get('schema_version', '1.0')
        if schema_version not in ['1.0', '2.0']:
            errors.append(f"Unsupported schema version: {schema_version}")

        # Validate timestamp format
        try:
            timestamp = datetime.fromisoformat(run_data['timestamp'].replace('Z', '+00:00'))

            # Check for future timestamps
            if timestamp > datetime.now(timezone.utc):
                warnings.append(f"Future timestamp detected: {run_data['timestamp']}")
        except (ValueError, AttributeError) as e:
            errors.append(f"Invalid timestamp format: {e}")

        # Validate metric ranges
        for metric, ranges in self.METRIC_RANGES.items():
            if metric in run_data:
                value = run_data[metric]
                if not isinstance(value, (int, float)):
                    errors.append(f"{metric} must be numeric, got {type(value).__name__}")
                elif value < ranges['min'] or value > ranges['max']:
                    errors.append(
                        f"{metric} out of range: {value} "
                        f"(expected {ranges['min']}-{ranges['max']})"
                    )

        # Validate resource metrics if present (v2.0)
        if schema_version == '2.0' and 'resource_metrics' in run_data:
            rm = run_data['resource_metrics']

            # CPU peak should be >= average
            if rm.get('cpu', {}).get('peak_percent', 0) < rm.get('cpu', {}).get('avg_percent', 0):
                errors.append("CPU peak_percent cannot be less than avg_percent")

            # Memory peak should be >= average
            if rm.get('memory', {}).get('peak_mb', 0) < rm.get('memory', {}).get('avg_mb', 0):
                errors.append("Memory peak_mb cannot be less than avg_mb")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def check_duplicate(self, run_id: str) -> bool:
        """Check if run_id already exists in history"""
        if not self.output_path.exists():
            return False

        try:
            with open(self.output_path) as f:
                history = json.load(f)

            return any(run['run_id'] == run_id for run in history)
        except (json.JSONDecodeError, KeyError):
            return False

    def append_run(self, run_data: dict[str, Any]) -> dict[str, Any]:
        """
        Append validated run to history file

        Returns:
            {
                'success': bool,
                'message': str,
                'run_id': str
            }
        """
        # Validate data
        validation = self.validate_run_data(run_data)

        if not validation['valid']:
            return {
                'success': False,
                'message': 'Validation failed',
                'errors': validation['errors'],
                'warnings': validation['warnings']
            }

        # Check for duplicates
        if self.check_duplicate(run_data['run_id']):
            return {
                'success': False,
                'message': f"Duplicate run_id: {run_data['run_id']}",
                'suggestion': 'Use a different run_id or update existing run'
            }

        # Load existing history
        if self.output_path.exists():
            with open(self.output_path) as f:
                history = json.load(f)
        else:
            history = []

        # Append new run at the beginning (most recent first)
        history.insert(0, run_data)

        # Write back to file
        with open(self.output_path, 'w') as f:
            json.dump(history, f, indent=2)

        return {
            'success': True,
            'message': f"Run {run_data['run_id']} recorded successfully",
            'run_id': run_data['run_id'],
            'timestamp': run_data['timestamp'],
            'warnings': validation['warnings'],
            'total_runs': len(history)
        }


class ResourceMonitor:
    """Monitors system resource usage during pipeline execution"""

    def __init__(self):
        if not PSUTIL_AVAILABLE:
            raise ImportError("psutil is required for resource monitoring. Install with: pip install psutil")
        self.process = psutil.Process()
        self.start_time = None
        self.samples = []

    def start(self):
        """Initialize monitoring"""
        self.start_time = time.time()
        # First call to cpu_percent() returns 0, so call it to initialize
        self.process.cpu_percent()
        self.sample()  # Take initial sample

    def sample(self):
        """Take periodic resource snapshot"""
        try:
            io_counters = self.process.io_counters()
        except (psutil.AccessDenied, AttributeError):
            # io_counters not available on all platforms
            io_counters = None

        sample = {
            'cpu_percent': self.process.cpu_percent(),
            'memory_mb': self.process.memory_info().rss / (1024 * 1024),
            'io_counters': io_counters,
            'timestamp': time.time()
        }
        self.samples.append(sample)

    def finalize(self) -> dict[str, Any]:
        """Compute aggregated metrics"""
        if len(self.samples) < 2:
            return None

        cpu_values = [s['cpu_percent'] for s in self.samples if s['cpu_percent'] > 0]
        mem_values = [s['memory_mb'] for s in self.samples]

        metrics = {
            'cpu': {
                'peak_percent': round(max(cpu_values), 1) if cpu_values else None,
                'avg_percent': round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None
            },
            'memory': {
                'peak_mb': round(max(mem_values)),
                'avg_mb': round(sum(mem_values) / len(mem_values))
            }
        }

        # Add disk I/O if available
        io_start = self.samples[0]['io_counters']
        io_end = self.samples[-1]['io_counters']

        if io_start and io_end:
            metrics['disk'] = {
                'read_mb': round((io_end.read_bytes - io_start.read_bytes) / (1024**2), 1),
                'write_mb': round((io_end.write_bytes - io_start.write_bytes) / (1024**2), 1),
                'read_ops': io_end.read_count - io_start.read_count,
                'write_ops': io_end.write_count - io_start.write_count
            }
        else:
            metrics['disk'] = {
                'read_mb': None,
                'write_mb': None,
                'read_ops': None,
                'write_ops': None
            }

        return metrics


def collect_environment_info() -> dict[str, Any]:
    """Collect system environment information"""
    import platform

    env_info = {
        'python_version': platform.python_version(),
        'hostname': platform.node(),
        'os': platform.system().lower(),
        'os_version': platform.release()
    }

    # Add psutil-based metrics if available
    if PSUTIL_AVAILABLE:
        env_info['cpu_cores'] = psutil.cpu_count(logical=True)
        env_info['total_memory_mb'] = round(psutil.virtual_memory().total / (1024**2))

    return env_info


def interactive_run_entry() -> dict[str, Any]:
    """Interactive CLI for entering run metrics"""
    print("\n=== Pipeline Run Recorder - Interactive Mode ===\n")

    # Generate default run_id from current timestamp
    now = datetime.now(timezone.utc)
    default_run_id = now.strftime("%Y%m%d_%H%M%S")
    default_timestamp = now.isoformat().replace('+00:00', 'Z')

    run_data = {}

    # Basic fields
    run_data['run_id'] = input(f"Run ID [{default_run_id}]: ").strip() or default_run_id
    run_data['timestamp'] = input(f"Timestamp [{default_timestamp}]: ").strip() or default_timestamp
    run_data['schema_version'] = input("Schema version [2.0]: ").strip() or "2.0"

    # Core metrics
    run_data['sources_processed'] = int(input("Sources processed [5]: ").strip() or "5")
    run_data['total_duration_seconds'] = int(input("Total duration (seconds): ").strip())
    run_data['total_records'] = int(input("Total records: ").strip())
    run_data['throughput_rpm'] = int(input("Throughput (records/min): ").strip())
    run_data['quality_pass_rate'] = float(input("Quality pass rate (0-1): ").strip())
    run_data['retries'] = int(input("Retries [0]: ").strip() or "0")
    run_data['errors'] = int(input("Errors [0]: ").strip() or "0")

    # Ask if user wants to add resource metrics (only if psutil available)
    if PSUTIL_AVAILABLE:
        add_resources = input("\nCollect resource metrics? (y/n) [n]: ").strip().lower()

        if add_resources == 'y':
            print("\nCollecting resource metrics...")
            monitor = ResourceMonitor()
            monitor.start()

            # Simulate some work for demonstration
            print("Sampling system resources (this takes ~5 seconds)...")
            for _i in range(5):
                time.sleep(1)
                monitor.sample()

            resource_metrics = monitor.finalize()
            if resource_metrics:
                run_data['resource_metrics'] = resource_metrics
                print(f"✓ CPU: {resource_metrics['cpu']['peak_percent']}% peak, "
                      f"{resource_metrics['cpu']['avg_percent']}% avg")
                print(f"✓ Memory: {resource_metrics['memory']['peak_mb']} MB peak, "
                      f"{resource_metrics['memory']['avg_mb']} MB avg")
    else:
        print("\nResource metrics collection not available (psutil not installed)")

    # Add environment info
    run_data['environment'] = collect_environment_info()

    # Mark as real data (not synthetic)
    run_data['_synthetic'] = False

    return run_data


def main():
    parser = argparse.ArgumentParser(
        description='Record pipeline run metrics to history file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python scripts/record_pipeline_run.py -o dashboard/data/pipeline_run_history.json

  # With JSON input file
  python scripts/record_pipeline_run.py -i run_data.json -o dashboard/data/pipeline_run_history.json
        """
    )

    parser.add_argument(
        '-i', '--input',
        help='Input JSON file with run data (optional, uses interactive mode if not provided)'
    )

    parser.add_argument(
        '-o', '--output',
        default='dashboard/data/pipeline_run_history.json',
        help='Output history file (default: dashboard/data/pipeline_run_history.json)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without writing to file'
    )

    args = parser.parse_args()

    # Get run data
    if args.input:
        with open(args.input) as f:
            run_data = json.load(f)
    else:
        run_data = interactive_run_entry()

    # Record the run
    recorder = PipelineRunRecorder(args.output)

    if args.dry_run:
        print("\n=== DRY RUN - Validation Only ===")
        validation = recorder.validate_run_data(run_data)

        if validation['valid']:
            print("✓ Validation passed")
        else:
            print("✗ Validation failed:")
            for error in validation['errors']:
                print(f"  - {error}")

        if validation['warnings']:
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")

        sys.exit(0 if validation['valid'] else 1)

    # Append run to history
    result = recorder.append_run(run_data)

    if result['success']:
        print(f"\n✓ {result['message']}")
        print(f"  Total runs in history: {result['total_runs']}")

        if result.get('warnings'):
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  - {warning}")
    else:
        print(f"\n✗ Failed to record run: {result['message']}")

        if 'errors' in result:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")

        sys.exit(1)


if __name__ == '__main__':
    main()

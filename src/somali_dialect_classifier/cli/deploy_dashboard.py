#!/usr/bin/env python3
"""
CLI tool for deploying dashboard metrics to GitHub Pages.

This tool automates the process of committing and pushing metrics files
to trigger dashboard rebuilds on GitHub Actions.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..deployment import DashboardDeployer, DeploymentConfig, create_default_config
from ..utils.logging_utils import setup_logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Deploy dashboard metrics to GitHub Pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy metrics with default settings
  somali-deploy-dashboard

  # Dry run to preview what would be deployed
  somali-deploy-dashboard --dry-run

  # Deploy without pushing (commit locally only)
  somali-deploy-dashboard --no-push

  # Disable validation (not recommended)
  somali-deploy-dashboard --no-validate

  # Deploy even with only one source (override batch mode)
  somali-deploy-dashboard --min-sources 1

  # Custom metrics directory
  somali-deploy-dashboard --metrics-dir ./my-metrics

  # Verbose logging
  somali-deploy-dashboard --verbose
        """,
    )

    parser.add_argument(
        "--metrics-dir",
        type=Path,
        help="Path to metrics directory (default: auto-detected from project root)",
    )

    parser.add_argument(
        "--git-remote",
        default="origin",
        help="Git remote name (default: origin)",
    )

    parser.add_argument(
        "--git-branch",
        default="main",
        help="Git branch name (default: main)",
    )

    parser.add_argument(
        "--commit-prefix",
        default="chore(metrics)",
        help="Commit message prefix (default: chore(metrics))",
    )

    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit locally but don't push to remote",
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip metrics validation (not recommended)",
    )

    parser.add_argument(
        "--no-batch",
        action="store_true",
        help="Disable batch mode (deploy immediately regardless of source count)",
    )

    parser.add_argument(
        "--min-sources",
        type=int,
        default=1,
        help="Minimum number of sources required for batch deployment (default: 1)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deployment without making changes",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Write logs to file",
    )

    return parser.parse_args()


def main():
    """Main CLI entry point."""
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.log_file) if args.log_file else logging.NullHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    try:
        # Create configuration
        if args.metrics_dir:
            config = DeploymentConfig(
                metrics_dir=args.metrics_dir,
                git_remote=args.git_remote,
                git_branch=args.git_branch,
                commit_prefix=args.commit_prefix,
                auto_push=not args.no_push,
                validate_metrics=not args.no_validate,
                batch_mode=not args.no_batch,
                min_sources_for_deploy=args.min_sources,
            )
        else:
            config = create_default_config()
            # Override defaults with CLI args
            config.git_remote = args.git_remote
            config.git_branch = args.git_branch
            config.commit_prefix = args.commit_prefix
            config.auto_push = not args.no_push
            config.validate_metrics = not args.no_validate
            config.batch_mode = not args.no_batch
            config.min_sources_for_deploy = args.min_sources

        # Display configuration
        logger.info("Deployment Configuration:")
        logger.info(f"  Metrics directory: {config.metrics_dir}")
        logger.info(f"  Git remote: {config.git_remote}")
        logger.info(f"  Git branch: {config.git_branch}")
        logger.info(f"  Auto-push: {config.auto_push}")
        logger.info(f"  Validate metrics: {config.validate_metrics}")
        logger.info(f"  Batch mode: {config.batch_mode}")
        if config.batch_mode:
            logger.info(f"  Min sources: {config.min_sources_for_deploy}")
        logger.info("")

        # Create deployer and execute
        deployer = DashboardDeployer(config)
        success = deployer.deploy(dry_run=args.dry_run)

        if success:
            sys.exit(0)
        else:
            logger.error("Deployment failed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\nDeployment cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()

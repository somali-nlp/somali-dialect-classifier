"""
Dashboard command implementations for somali-tools CLI.

This module contains testable library code for dashboard operations.
Separated from CLI to enable unit testing without Click framework.

Functions include:
- Dashboard build orchestration
- Local development server
- Dashboard deployment
"""

import http.server
import logging
import shutil
import socketserver
import subprocess
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# DASHBOARD BUILD
# ============================================================================


def build_dashboard(
    clean: bool = False,
    verbose: bool = False
) -> dict[str, Any]:
    """
    Build dashboard site.

    Args:
        clean: If True, clean _site directory before building
        verbose: If True, show detailed build output

    Returns:
        Build result with status

    Raises:
        FileNotFoundError: If build script doesn't exist
        subprocess.CalledProcessError: If build fails
    """
    # Find project root and build script.
    #
    # Note: After the codebase restructuring, the dashboard lives under
    # src/dashboard, but we continue to emit the built site to the project
    # root _site/ directory so that GitHub Pages workflows and local tooling
    # can keep their existing assumptions.
    project_root = Path(__file__).parent.parent.parent.parent
    dashboard_dir = project_root / "src" / "dashboard"
    build_script = dashboard_dir / "build-site.sh"

    if not build_script.exists():
        raise FileNotFoundError(f"Build script not found: {build_script}")

    # Clean if requested
    site_dir = project_root / "_site"
    if clean and site_dir.exists():
        logger.info(f"Cleaning {site_dir}")
        shutil.rmtree(site_dir)

    # Run build script
    logger.info("Building dashboard...")

    try:
        result = subprocess.run(
            ["bash", str(build_script)],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )

        if verbose:
            logger.info(result.stdout)

        # Verify build output
        if not site_dir.exists():
            raise RuntimeError("Build completed but _site directory not created")

        # Count generated files
        html_files = list(site_dir.rglob("*.html"))
        js_files = list(site_dir.rglob("*.js"))
        data_files = list(site_dir.rglob("*.json"))

        logger.info(
            f"Dashboard built successfully: "
            f"{len(html_files)} HTML, {len(js_files)} JS, {len(data_files)} JSON files"
        )

        return {
            "status": "success",
            "site_dir": str(site_dir),
            "files": {
                "html": len(html_files),
                "js": len(js_files),
                "json": len(data_files)
            },
            "cleaned": clean,
            "verbose": verbose
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Build failed: {e.stderr}")
        raise RuntimeError(f"Build failed: {e.stderr}")


# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================


class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with minimal logging."""

    def log_message(self, format, *args):
        """Suppress request logging unless verbose."""
        pass


def serve_dashboard(
    port: int = 8000,
    host: str = "127.0.0.1"
) -> None:
    """
    Start local development server.

    Args:
        port: Port for development server
        host: Host for development server

    Raises:
        FileNotFoundError: If _site directory doesn't exist
        OSError: If port is already in use
    """
    # Find _site directory
    project_root = Path(__file__).parent.parent.parent.parent
    site_dir = project_root / "_site"

    if not site_dir.exists():
        raise FileNotFoundError(
            f"Dashboard not built. Run 'somali-tools dashboard build' first. "
            f"Expected directory: {site_dir}"
        )

    # Change to site directory
    import os
    original_dir = os.getcwd()

    try:
        os.chdir(site_dir)

        # Create server
        with socketserver.TCPServer((host, port), SilentHTTPRequestHandler) as httpd:
            logger.info(f"Serving dashboard at http://{host}:{port}")
            logger.info("Press Ctrl+C to stop")

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.info("\nShutting down server")

    finally:
        os.chdir(original_dir)


# ============================================================================
# DASHBOARD DEPLOYMENT
# ============================================================================


def deploy_dashboard(
    target: str = "github-pages",
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Deploy dashboard to specified target.

    Args:
        target: Deployment target (github-pages, netlify, s3)
        dry_run: If True, show what would be deployed without executing

    Returns:
        Deployment result

    Raises:
        ValueError: If target not supported
        FileNotFoundError: If _site directory doesn't exist
    """
    supported_targets = ["github-pages", "netlify", "s3"]
    if target not in supported_targets:
        raise ValueError(
            f"Unsupported target: {target}. "
            f"Supported: {', '.join(supported_targets)}"
        )

    # Find _site directory
    project_root = Path(__file__).parent.parent.parent.parent
    site_dir = project_root / "_site"

    if not site_dir.exists():
        raise FileNotFoundError(
            f"Dashboard not built. Run 'somali-tools dashboard build' first. "
            f"Expected directory: {site_dir}"
        )

    if target == "github-pages":
        return deploy_to_github_pages(site_dir, dry_run)
    elif target == "netlify":
        return deploy_to_netlify(site_dir, dry_run)
    elif target == "s3":
        return deploy_to_s3(site_dir, dry_run)


def deploy_to_github_pages(
    site_dir: Path,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Deploy dashboard to GitHub Pages.

    Args:
        site_dir: Path to _site directory
        dry_run: If True, show what would be deployed

    Returns:
        Deployment result
    """
    if dry_run:
        logger.info("[DRY RUN] Would deploy to GitHub Pages")
        logger.info(f"  Source: {site_dir}")
        logger.info("  Command: gh-pages -d _site")
        return {
            "status": "dry_run",
            "target": "github-pages",
            "site_dir": str(site_dir)
        }

    # Check if gh-pages CLI is available
    try:
        subprocess.run(
            ["gh-pages", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "gh-pages CLI not found. Install with: npm install -g gh-pages"
        )

    # Deploy
    logger.info("Deploying to GitHub Pages...")

    try:
        result = subprocess.run(
            ["gh-pages", "-d", str(site_dir)],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info("Deployment successful")
        return {
            "status": "success",
            "target": "github-pages",
            "site_dir": str(site_dir)
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: {e.stderr}")
        raise RuntimeError(f"Deployment failed: {e.stderr}")


def deploy_to_netlify(
    site_dir: Path,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Deploy dashboard to Netlify.

    Args:
        site_dir: Path to _site directory
        dry_run: If True, show what would be deployed

    Returns:
        Deployment result
    """
    if dry_run:
        logger.info("[DRY RUN] Would deploy to Netlify")
        logger.info(f"  Source: {site_dir}")
        logger.info("  Command: netlify deploy --prod --dir _site")
        return {
            "status": "dry_run",
            "target": "netlify",
            "site_dir": str(site_dir)
        }

    # Check if netlify CLI is available
    try:
        subprocess.run(
            ["netlify", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "Netlify CLI not found. Install with: npm install -g netlify-cli"
        )

    # Deploy
    logger.info("Deploying to Netlify...")

    try:
        result = subprocess.run(
            ["netlify", "deploy", "--prod", "--dir", str(site_dir)],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info("Deployment successful")
        logger.info(result.stdout)

        return {
            "status": "success",
            "target": "netlify",
            "site_dir": str(site_dir)
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: {e.stderr}")
        raise RuntimeError(f"Deployment failed: {e.stderr}")


def deploy_to_s3(
    site_dir: Path,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Deploy dashboard to AWS S3.

    Args:
        site_dir: Path to _site directory
        dry_run: If True, show what would be deployed

    Returns:
        Deployment result
    """
    if dry_run:
        logger.info("[DRY RUN] Would deploy to AWS S3")
        logger.info(f"  Source: {site_dir}")
        logger.info("  Note: S3 bucket must be configured in environment")
        return {
            "status": "dry_run",
            "target": "s3",
            "site_dir": str(site_dir)
        }

    # Check if AWS CLI is available
    try:
        subprocess.run(
            ["aws", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "AWS CLI not found. Install with: pip install awscli"
        )

    # Get S3 bucket from environment
    import os
    bucket = os.environ.get("DASHBOARD_S3_BUCKET")

    if not bucket:
        raise RuntimeError(
            "DASHBOARD_S3_BUCKET environment variable not set. "
            "Set with: export DASHBOARD_S3_BUCKET=your-bucket-name"
        )

    # Deploy
    logger.info(f"Deploying to S3 bucket: {bucket}")

    try:
        result = subprocess.run(
            [
                "aws", "s3", "sync",
                str(site_dir),
                f"s3://{bucket}/",
                "--delete"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info("Deployment successful")
        return {
            "status": "success",
            "target": "s3",
            "bucket": bucket,
            "site_dir": str(site_dir)
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: {e.stderr}")
        raise RuntimeError(f"Deployment failed: {e.stderr}")

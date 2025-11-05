#!/usr/bin/env python3
"""
Generate Quality Feed Data

Parses quality reports from data/reports/ and generates:
- dashboard/data/quality_alerts.json: Exception feed with actionable alerts
- dashboard/data/quality_waivers.json: Policy & waiver log

This script is part of the dashboard data pipeline and runs during CI/CD.

Schema Contract:
    - Input: data/reports/*_final_quality_report.md
    - Output: dashboard/data/quality_alerts.json
    - Output: dashboard/data/quality_waivers.json

Usage:
    python scripts/generate_quality_feed.py
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict


def parse_quality_report(report_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse a quality report markdown file.

    Args:
        report_path: Path to the quality report markdown file

    Returns:
        Dictionary with parsed report data or None if parsing failed
    """
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract metadata
        run_id_match = re.search(r'\*\*Run ID:\*\* (\S+)', content)
        source_match = re.search(r'\*\*Source:\*\* (.+)', content)
        timestamp_match = re.search(r'\*\*Timestamp:\*\* (\S+)', content)
        status_match = re.search(r'\*\*Pipeline Status:\*\* ([❌✅]) \*\*(\w+)\*\*', content)

        if not all([run_id_match, source_match, timestamp_match, status_match]):
            print(f"Warning: Failed to parse metadata from {report_path.name}", file=sys.stderr)
            return None

        run_id = run_id_match.group(1)
        source = source_match.group(1)
        timestamp = timestamp_match.group(1)
        status_emoji = status_match.group(1)
        status = status_match.group(2)

        # Extract quality pass rate
        quality_rate_match = re.search(r'Quality Filter Pass Rate:\*\* ([\d.]+)%', content)
        quality_pass_rate = float(quality_rate_match.group(1)) if quality_rate_match else None

        # Extract recommendations
        recommendations_section = re.search(r'## Recommendations\n\n(.+?)\n\n---', content, re.DOTALL)
        recommendations = recommendations_section.group(1).strip() if recommendations_section else ""

        # Extract filter statistics
        filter_stats = {}
        filter_table_match = re.search(r'\| Filter Reason \| Count \| Percentage \|(.+?)---', content, re.DOTALL)
        if filter_table_match:
            filter_lines = filter_table_match.group(1).strip().split('\n')
            for line in filter_lines:
                if '|' in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3:
                        filter_name = parts[0]
                        count = parts[1].replace(',', '')
                        percentage = parts[2].rstrip('%')
                        try:
                            filter_stats[filter_name] = {
                                "count": int(count),
                                "percentage": float(percentage)
                            }
                        except ValueError:
                            pass

        return {
            "run_id": run_id,
            "source": source,
            "timestamp": timestamp,
            "status": status,
            "status_emoji": status_emoji,
            "quality_pass_rate": quality_pass_rate,
            "recommendations": recommendations,
            "filter_stats": filter_stats,
            "report_path": str(report_path)
        }

    except Exception as e:
        print(f"Error parsing {report_path.name}: {e}", file=sys.stderr)
        return None


def generate_quality_alerts(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate quality alerts from parsed reports.

    Creates actionable alerts for:
    - Unhealthy pipelines
    - Low quality pass rates
    - High filter rejection rates
    - Performance issues

    Args:
        reports: List of parsed report dictionaries

    Returns:
        Quality alerts data structure
    """
    alerts = []
    alert_id = 1

    for report in reports:
        source = report["source"]
        status = report["status"]
        quality_pass_rate = report["quality_pass_rate"]
        recommendations = report["recommendations"]
        report_path = report["report_path"]
        timestamp = report["timestamp"]

        # Generate relative path for GitHub Pages
        # Convert: /path/to/data/reports/report.md -> data/reports/report.md
        relative_report_path = "data/reports/" + Path(report_path).name

        # Alert 1: Unhealthy pipeline status
        if status == "UNHEALTHY":
            severity = "high"
            message = f"{source} pipeline status is UNHEALTHY."

            # Extract specific issue from recommendations
            recommendation = "Investigate root cause and resolve pipeline issues."
            if "Stream connection failed" in recommendations:
                message += " Stream connection failed."
                recommendation = "Check API credentials, network connectivity, rate limits, and authentication tokens. Review service logs for connection errors."
            elif "connection" in recommendations.lower():
                message += " Connection issues detected."
                recommendation = "Check network connectivity, firewall rules, and service availability. Review connection logs."

            alerts.append({
                "id": f"alert-{alert_id}",
                "severity": severity,
                "message": message,
                "source": source,
                "timestamp": timestamp,
                "report_url": relative_report_path,
                "details": recommendations.replace('❌', '').replace('🐢', '').replace('✅', '').strip(),
                "recommendation": recommendation
            })
            alert_id += 1

        # Alert 2: Low quality pass rate (below 70%)
        if quality_pass_rate is not None and quality_pass_rate < 70.0:
            severity = "medium" if quality_pass_rate >= 50.0 else "high"
            message = f"{source} quality pass rate at {quality_pass_rate:.1f}% is below the 70% threshold."

            # Provide actionable recommendation based on severity
            if quality_pass_rate < 50.0:
                recommendation = "Review filter policies immediately. High rejection rate may indicate data quality issues or overly strict filters. Analyze filter breakdown and adjust thresholds."
            else:
                recommendation = "Review filter breakdown to identify primary rejection reasons. Consider adjusting filter thresholds or improving source data quality."

            alerts.append({
                "id": f"alert-{alert_id}",
                "severity": severity,
                "message": message,
                "source": source,
                "timestamp": timestamp,
                "report_url": relative_report_path,
                "details": f"Quality filter pass rate: {quality_pass_rate:.1f}%",
                "recommendation": recommendation
            })
            alert_id += 1

        # Alert 3: Performance issues (slow fetch times)
        if "slow fetch" in recommendations.lower() or "🐢" in recommendations:
            severity = "low"
            message = f"{source} experiencing slow fetch times."
            recommendation = "Implement connection pooling, adjust timeouts, or use concurrent requests. Consider adding caching layer for frequently accessed content."

            alerts.append({
                "id": f"alert-{alert_id}",
                "severity": severity,
                "message": message,
                "source": source,
                "timestamp": timestamp,
                "report_url": relative_report_path,
                "details": recommendations.replace('❌', '').replace('🐢', '').replace('✅', '').strip(),
                "recommendation": recommendation
            })
            alert_id += 1

        # Alert 4: High filter rejection rate for specific filters (above 80%)
        for filter_name, stats in report["filter_stats"].items():
            if stats["percentage"] > 80.0:
                severity = "medium"
                message = f"{source} has high {filter_name} rejection rate at {stats['percentage']:.1f}%."

                # Provide filter-specific recommendations
                if "emoji" in filter_name.lower():
                    recommendation = "High emoji-only rejection is expected for social media sources. Review policy to ensure it aligns with data quality goals."
                elif "length" in filter_name.lower():
                    recommendation = "Review minimum length thresholds. Consider if source characteristics justify current limits or if adjustment is needed."
                elif "langid" in filter_name.lower() or "language" in filter_name.lower():
                    recommendation = "High language filter rejection may indicate mixed-language content. Review language detection accuracy and thresholds."
                else:
                    recommendation = "Review filter policy and thresholds. High rejection rate may indicate overly strict filtering or source data quality issues."

                alerts.append({
                    "id": f"alert-{alert_id}",
                    "severity": severity,
                    "message": message,
                    "source": source,
                    "timestamp": timestamp,
                    "report_url": relative_report_path,
                    "details": f"{filter_name}: {stats['count']:,} records ({stats['percentage']:.1f}%)",
                    "recommendation": recommendation
                })
                alert_id += 1

    return {
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_alerts": len(alerts)
    }


def generate_quality_waivers(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate quality waivers from parsed reports.

    Creates waivers for:
    - Known low quality pass rates that are acceptable
    - Temporary pipeline issues under investigation
    - Filter policy exceptions

    Args:
        reports: List of parsed report dictionaries

    Returns:
        Quality waivers data structure
    """
    waivers = []
    waiver_id = 1

    # Define waiver policies based on actual data
    # These represent intentional exceptions to standard quality thresholds

    for report in reports:
        source = report["source"]
        status = report["status"]
        quality_pass_rate = report["quality_pass_rate"]
        timestamp = report["timestamp"]
        report_path = report["report_path"]

        # Generate relative path for GitHub Pages
        relative_report_path = "data/reports/" + Path(report_path).name

        # Parse timestamp for expiration calculation
        try:
            report_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            expiry_date = report_date + timedelta(days=45)  # 45-day waiver period
            granted_date = report_date
        except:
            granted_date = datetime.now(timezone.utc)
            expiry_date = granted_date + timedelta(days=45)

        # Waiver 1: Wikipedia low pass rate is expected (encyclopedia content)
        if source == "Wikipedia-Somali" and quality_pass_rate is not None and quality_pass_rate < 70.0:
            waivers.append({
                "id": f"waiver-{waiver_id}",
                "name": f"{source} Low Pass Rate",
                "status": "Active",
                "granted_on": granted_date.strftime("%Y-%m-%d"),
                "expires_on": expiry_date.strftime("%Y-%m-%d"),
                "owner": "Data Quality Team",
                "reason": f"Encyclopedia content naturally has higher filtering rate due to article structure and formatting. Current rate: {quality_pass_rate:.1f}%",
                "report_url": relative_report_path
            })
            waiver_id += 1

        # Waiver 2: TikTok stream connection issues (known infrastructure limitation)
        if source == "TikTok-Somali" and status == "UNHEALTHY":
            waivers.append({
                "id": f"waiver-{waiver_id}",
                "name": f"{source} Stream Connection",
                "status": "Active",
                "granted_on": granted_date.strftime("%Y-%m-%d"),
                "expires_on": expiry_date.strftime("%Y-%m-%d"),
                "owner": "Social Media Squad",
                "reason": "API rate limiting and connection stability issues under investigation. Deployment authorized with reduced volume.",
                "report_url": relative_report_path
            })
            waiver_id += 1

        # Waiver 3: emoji_only_comment filter (expected for social media)
        if "emoji_only_comment" in report["filter_stats"]:
            emoji_stats = report["filter_stats"]["emoji_only_comment"]
            if emoji_stats["percentage"] > 70.0:
                waivers.append({
                    "id": f"waiver-{waiver_id}",
                    "name": f"{source} Emoji-Only Content",
                    "status": "Active",
                    "granted_on": granted_date.strftime("%Y-%m-%d"),
                    "expires_on": expiry_date.strftime("%Y-%m-%d"),
                    "owner": "Content Policy Team",
                    "reason": f"High emoji-only comment rate ({emoji_stats['percentage']:.1f}%) is expected for social media sources. Filter policy approved.",
                    "report_url": relative_report_path
                })
                waiver_id += 1

    return {
        "waivers": waivers,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_waivers": len(waivers)
    }


def main():
    """Main execution function."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    reports_dir = project_root / "data" / "reports"
    output_dir = project_root / "dashboard" / "data"

    print("=" * 60)
    print("Quality Feed Generator")
    print("=" * 60)

    # Find final quality reports
    print(f"\n[1/4] Scanning for quality reports in: {reports_dir}")

    if not reports_dir.exists():
        print(f"Error: Reports directory not found: {reports_dir}", file=sys.stderr)
        sys.exit(1)

    report_files = sorted(reports_dir.glob("*_final_quality_report.md"))

    if not report_files:
        print(f"Warning: No final quality reports found in {reports_dir}", file=sys.stderr)
        # Create empty files
        output_dir.mkdir(parents=True, exist_ok=True)

        empty_alerts = {
            "alerts": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_alerts": 0
        }

        empty_waivers = {
            "waivers": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_waivers": 0
        }

        with open(output_dir / "quality_alerts.json", 'w', encoding='utf-8') as f:
            json.dump(empty_alerts, f, indent=2)

        with open(output_dir / "quality_waivers.json", 'w', encoding='utf-8') as f:
            json.dump(empty_waivers, f, indent=2)

        print("✓ Created empty alert and waiver files")
        return

    print(f"✓ Found {len(report_files)} quality reports")

    # Parse all reports
    print(f"\n[2/4] Parsing quality reports...")
    reports = []

    for report_file in report_files:
        parsed = parse_quality_report(report_file)
        if parsed:
            reports.append(parsed)
            print(f"  ✓ Parsed: {report_file.name}")

    if not reports:
        print("Error: No reports could be parsed", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Successfully parsed {len(reports)} reports")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate quality alerts
    print(f"\n[3/4] Generating quality alerts...")
    alerts_data = generate_quality_alerts(reports)

    alerts_file = output_dir / "quality_alerts.json"
    with open(alerts_file, 'w', encoding='utf-8') as f:
        json.dump(alerts_data, f, indent=2)

    print(f"✓ Wrote {alerts_data['total_alerts']} alerts to: {alerts_file}")

    # Show alert summary
    if alerts_data["alerts"]:
        severity_counts = defaultdict(int)
        for alert in alerts_data["alerts"]:
            severity_counts[alert["severity"]] += 1

        print(f"  - High severity: {severity_counts['high']}")
        print(f"  - Medium severity: {severity_counts['medium']}")
        print(f"  - Low severity: {severity_counts['low']}")

    # Generate quality waivers
    print(f"\n[4/4] Generating quality waivers...")
    waivers_data = generate_quality_waivers(reports)

    waivers_file = output_dir / "quality_waivers.json"
    with open(waivers_file, 'w', encoding='utf-8') as f:
        json.dump(waivers_data, f, indent=2)

    print(f"✓ Wrote {waivers_data['total_waivers']} waivers to: {waivers_file}")

    # Show waiver summary
    if waivers_data["waivers"]:
        for waiver in waivers_data["waivers"]:
            print(f"  - {waiver['name']}: {waiver['reason'][:50]}...")

    print("\n" + "=" * 60)
    print("Quality feed generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

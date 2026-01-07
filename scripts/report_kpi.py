#!/usr/bin/env python3
"""
KPI Report Generator
Generates a performance report for Dhamma Channel
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from googleapiclient.errors import HttpError
from jinja2 import Environment, FileSystemLoader

from agents.analytics_agent import AnalyticsAgent, AnalyticsInput
from agents.analytics_agent.adapter import YouTubeAnalyticsAdapter
from agents.analytics_agent.mock import MockYouTubeAnalyticsAdapter


def generate_html_report(output_data, output_file: Path):
    """Generate HTML Report using Jinja2"""

    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("kpi_report.html")

    html = template.render(data=output_data)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Report generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate KPI Report")
    parser.add_argument("--days", default="30d", help="Date range (7d, 30d, 90d)")
    parser.add_argument(
        "--out", default="reports/kpi_report.html", help="Output file path"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Use mock data without API calls"
    )

    args = parser.parse_args()

    print(f"🚀 Starting KPI Report Generator ({args.days})")

    if args.dry_run:
        print("🔧 Mode: DRY RUN (Mock Data)")
        adapter = MockYouTubeAnalyticsAdapter()
    else:
        print("🔧 Mode: PRODUCTION (Real API)")
        # Load credentials setup
        creds_json = Path(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "client_secret.json")
        )  # Default lookup
        token_json = Path("youtube_token.json")

        # Check if secrets exist (simple check, adapter does more)
        if not creds_json.exists() and not token_json.exists():
            print(f"❌ Credentials not found at {creds_json}")
            print(
                "   Please enable YouTube Analytics API and download client_secret.json"
            )
            return 1

        adapter = YouTubeAnalyticsAdapter(creds_json, token_json)

        try:
            adapter.authenticate()
        except (RuntimeError, ValueError) as e:
            print(f"❌ Authentication failed: {e}")
            return 1
        except Exception as e:  # Catch unexpected errors
            print(f"❌ Unexpected error during authentication: {e}")
            return 1

    agent = AnalyticsAgent(adapter=adapter)

    try:
        input_data = AnalyticsInput(date_range=args.days)
        result = agent.run(input_data)

        # Generate HTML
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_html_report(result, output_path)

    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Generate a structured session report for sharing with a human therapist.

Calls stillpoint.report.generate_session_report() and saves the result to a
Markdown file. stillpoint/report.py is built in a parallel worktree — the
import resolves at runtime after merge. A clear error is shown if missing.

Usage:
    python scripts/generate_report.py [--since DATE] [--sections s1,s2,...] \\
                                      [--anonymize] [--output PATH]

Examples:
    python scripts/generate_report.py
    python scripts/generate_report.py --since 2026-05-01
    python scripts/generate_report.py --anonymize --output reports/for_dr_smith.md
    python scripts/generate_report.py --sections themes,goals,red_flags
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


IMPORT_ERROR_MSG = """
Error: stillpoint.report is not yet available.

stillpoint/report.py is being implemented in a parallel worktree and will
resolve after the branches are merged. In the meantime you can:

  1. Wait for the merge, then re-run this script.
  2. Implement stillpoint/report.py manually — see ARCHITECTURE.md for the API.

Required function signature:
    from stillpoint.report import generate_session_report
    generate_session_report(sessions=None, sections=None, anonymize=False) -> str
"""

VALID_SECTIONS = [
    "themes",
    "goals",
    "disclosures",
    "coping",
    "trajectory",
    "red_flags",
    "patterns",
    "homework",
    "client_words",
]


def get_project_root() -> Path:
    """Return the project root (parent of this script's directory)."""
    return Path(__file__).resolve().parent.parent


def get_default_output_path() -> Path:
    """Return the default report path with today's date."""
    reports_dir = get_project_root() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return reports_dir / f"report_{date_str}.md"


def parse_sections(sections_arg: str | None) -> list[str] | None:
    """Parse and validate the --sections argument.

    Args:
        sections_arg: Comma-separated section names, or None.

    Returns:
        List of valid section names, or None if argument was not provided.
    """
    if sections_arg is None:
        return None

    requested = [s.strip() for s in sections_arg.split(",")]
    invalid = [s for s in requested if s not in VALID_SECTIONS]
    if invalid:
        print(f"Unknown sections: {', '.join(invalid)}", file=sys.stderr)
        print(f"Valid sections: {', '.join(VALID_SECTIONS)}", file=sys.stderr)
        sys.exit(1)

    return requested


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a session report for sharing with a human therapist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )
    parser.add_argument(
        "--since",
        metavar="DATE",
        help="Only include sessions from this date onward (YYYY-MM-DD). "
             "Default: all sessions since last report.",
    )
    parser.add_argument(
        "--sections",
        metavar="s1,s2,...",
        help=(
            f"Comma-separated sections to include. "
            f"Valid: {', '.join(VALID_SECTIONS)}. "
            f"Default: all sections."
        ),
    )
    parser.add_argument(
        "--anonymize",
        action="store_true",
        help="Anonymize names and identifying details in the report.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        type=Path,
        help="Output file path (default: reports/report_YYYY-MM-DD.md).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        from stillpoint.report import generate_session_report
    except ImportError:
        print(IMPORT_ERROR_MSG, file=sys.stderr)
        sys.exit(1)

    sections = parse_sections(args.sections)
    output_path = args.output or get_default_output_path()

    print(f"Generating report...")
    if args.since:
        print(f"  Sessions since: {args.since}")
    if sections:
        print(f"  Sections: {', '.join(sections)}")
    if args.anonymize:
        print(f"  Anonymization: enabled")

    try:
        report_content = generate_session_report(
            since=args.since,
            sections=sections,
            anonymize=args.anonymize,
        )
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)

    if not report_content:
        print("No session data found for the specified criteria.", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Report saved: {output_path}")

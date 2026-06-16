"""Save or export a session from Stillpoint memory storage.

Usage:
    python scripts/save_session.py [--session-id ID] [--output PATH] [--list]

Examples:
    python scripts/save_session.py --list
    python scripts/save_session.py --session-id 20260516_143022 --output my_session.md
    python scripts/save_session.py  # saves most recent session to exports/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Return the project root (parent of this script's directory)."""
    return Path(__file__).resolve().parent.parent


def get_memory_dir() -> Path:
    """Return the memory storage directory."""
    return get_project_root() / "config" / "sessions"


def load_session_index() -> list[dict]:
    """Load the session index file."""
    index_path = get_memory_dir() / "index.json"
    if not index_path.exists():
        return []
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_session(session_id: str) -> dict | None:
    """Load a single session by ID.

    Args:
        session_id: The session ID (e.g., '20260516_143022').

    Returns:
        Session dict with 'id', 'timestamp', 'content', or None if not found.
    """
    session_path = get_memory_dir() / f"session_{session_id}.json"
    if not session_path.exists():
        return None
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_session_as_markdown(session: dict) -> str:
    """Format a session dict as a Markdown document.

    Args:
        session: Session dict with 'id', 'timestamp', 'content'.

    Returns:
        Markdown string.
    """
    ts = session.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts)
        date_str = dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        date_str = ts or "Unknown"

    lines = [
        "# Session Export",
        "",
        f"**Session ID**: {session.get('id', 'unknown')}  ",
        f"**Date**: {date_str}",
        "",
        "---",
        "",
        session.get("content", "*(no content)*"),
    ]
    return "\n".join(lines)


def get_default_output_path() -> Path:
    """Return the default export path with today's date."""
    exports_dir = get_project_root() / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return exports_dir / f"session_{date_str}.md"


def list_sessions() -> None:
    """Print all available session IDs to stdout."""
    index = load_session_index()
    if not index:
        print("No sessions found. Run a therapy session first.")
        return

    print(f"{'ID':<20}  {'Date':<20}  Preview")
    print("-" * 70)
    for entry in index:
        ts = entry.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = ts[:19] if ts else "Unknown"

        preview = entry.get("preview", "")[:35].replace("\n", " ")
        print(f"{entry['id']:<20}  {date_str:<20}  {preview}")

    print(f"\n{len(index)} session(s) total.")


def save_session(session_id: str | None, output: Path) -> int:
    """Load a session and write it to a Markdown file.

    Args:
        session_id: The session ID to load, or None for the most recent.
        output: Destination file path.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    index = load_session_index()
    if not index:
        print("No sessions found. Run a therapy session first.", file=sys.stderr)
        return 1

    if session_id is None:
        # Use the most recent session
        session_id = index[-1]["id"]
        print(f"No session ID specified — using most recent: {session_id}")

    session = load_session(session_id)
    if session is None:
        print(f"Session '{session_id}' not found.", file=sys.stderr)
        print("Use --list to see available sessions.", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    content = format_session_as_markdown(session)
    with open(output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Session saved: {output}")
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Save or export a Stillpoint therapy session.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )
    parser.add_argument(
        "--session-id",
        metavar="ID",
        help="Session ID to export (default: most recent). Use --list to see IDs.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        type=Path,
        help="Output file path (default: exports/session_YYYY-MM-DD.md).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available session IDs and exit.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.list:
        list_sessions()
        sys.exit(0)

    output_path = args.output or get_default_output_path()
    sys.exit(save_session(args.session_id, output_path))

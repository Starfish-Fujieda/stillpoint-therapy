"""Generate a therapy podcast episode.

Calls stillpoint.podcast.generate_podcast() and prints the path to the
generated audio file. stillpoint/podcast.py is built in a parallel worktree —
the import resolves at runtime after merge. A clear error is shown if missing.

Usage:
    python scripts/generate_podcast.py [--topic TOPIC] [--method METHOD] \\
                                       [--impetus TEXT] [--intended-takeaways TEXT]

Methods:
    notebooklm  Use NotebookLM Audio Overview (requires notebooklm CLI auth).
    local       Use Podcastfy + local TTS (requires podcastfy installed).

Examples:
    python scripts/generate_podcast.py
    python scripts/generate_podcast.py --topic anxiety_ocd
    python scripts/generate_podcast.py --topic cptsd_trauma --method notebooklm
    python scripts/generate_podcast.py --topic anxiety_ocd \\
        --impetus "user reported rising anxiety this week" \\
        --intended-takeaways "normalize anxiety; introduce urge-surfing"
"""

import argparse
import sys

IMPORT_ERROR_MSG = """
Error: stillpoint.podcast is not yet available.

stillpoint/podcast.py is being implemented in a parallel worktree and will
resolve after the branches are merged. In the meantime you can:

  1. Wait for the merge, then re-run this script.
  2. Implement stillpoint/podcast.py manually — see ARCHITECTURE.md for the API.

Required function signature:
    from stillpoint.podcast import generate_podcast
    generate_podcast(topic=None, method="notebooklm",
                     impetus="", intended_takeaways="") -> str
"""

VALID_METHODS = ["notebooklm", "local"]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a therapy podcast episode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )
    parser.add_argument(
        "--topic",
        metavar="TOPIC",
        help=(
            "Clinical topic key to generate a podcast about "
            "(e.g., 'anxiety_ocd', 'cptsd_trauma'). "
            "Run podcast_gap_analyzer.py --suggest for the recommended next topic. "
            "If omitted, the podcast module selects automatically."
        ),
    )
    parser.add_argument(
        "--method",
        metavar="METHOD",
        default="notebooklm",
        choices=VALID_METHODS,
        help=(
            f"Generation method: {' | '.join(VALID_METHODS)}. "
            f"Default: notebooklm."
        ),
    )
    parser.add_argument(
        "--impetus",
        metavar="TEXT",
        default="",
        help=(
            "Why this episode is being generated — what prompted it. "
            "Recorded in config/podcast_registry.yaml."
        ),
    )
    parser.add_argument(
        "--intended-takeaways",
        metavar="TEXT",
        default="",
        help=(
            "What the user should come away with from this episode. "
            "Recorded in config/podcast_registry.yaml."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        from stillpoint.podcast import generate_podcast
    except ImportError:
        print(IMPORT_ERROR_MSG, file=sys.stderr)
        sys.exit(1)

    topic_label = args.topic or "(auto-selected)"
    print("Generating podcast...")
    print(f"  Topic:  {topic_label}")
    print(f"  Method: {args.method}")
    if args.impetus:
        print(f"  Impetus: {args.impetus}")
    if args.intended_takeaways:
        print(f"  Intended takeaways: {args.intended_takeaways}")

    try:
        audio_path = generate_podcast(
            topic=args.topic,
            method=args.method,
            impetus=args.impetus,
            intended_takeaways=args.intended_takeaways,
        )
    except Exception as e:
        print(f"Error generating podcast: {e}", file=sys.stderr)
        sys.exit(1)

    if not audio_path:
        print("Podcast generation returned no output path.", file=sys.stderr)
        sys.exit(1)

    print(f"Podcast generated: {audio_path}")

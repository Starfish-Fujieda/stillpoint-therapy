"""Analyze which clinical topics have not yet been covered by any podcast.

Reads templates/source_library.yaml for the full topic list and scans the
podcasts/ directory (or a metadata file) to determine what has been generated.
Outputs uncovered topics ranked by priority based on treatment plan goals.

Usage:
    python scripts/podcast_gap_analyzer.py [--topics-file PATH] [--suggest]

Examples:
    python scripts/podcast_gap_analyzer.py
    python scripts/podcast_gap_analyzer.py --suggest
    python scripts/podcast_gap_analyzer.py --topics-file templates/source_library.yaml
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


def get_project_root() -> Path:
    """Return the project root (parent of this script's directory)."""
    return Path(__file__).resolve().parent.parent


def load_topics(topics_file: Path) -> dict[str, dict]:
    """Load all clinical topics from the source library.

    Args:
        topics_file: Path to source_library.yaml.

    Returns:
        Dict mapping topic_key -> topic metadata.
    """
    with open(topics_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("topics", {})


def discover_covered_topics(podcasts_dir: Path) -> set[str]:
    """Scan the podcasts directory to find which topics have been covered.

    Checks both audio files and a metadata JSON (podcast_index.json if present).

    Args:
        podcasts_dir: Path to the podcasts directory.

    Returns:
        Set of topic keys that have been covered.
    """
    covered: set[str] = set()

    if not podcasts_dir.exists():
        return covered

    # Check for a metadata index first
    index_path = podcasts_dir / "podcast_index.json"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        for entry in index:
            topic = entry.get("topic") or entry.get("topic_key")
            if topic:
                covered.add(topic)
        return covered

    # Fallback: infer topic from audio filenames (e.g., anxiety_ocd_20260516.mp3)
    audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
    for f in podcasts_dir.iterdir():
        if f.suffix.lower() in audio_extensions:
            # Strip date suffix and try to match topic key
            stem = re.sub(r"_\d{8}.*$", "", f.stem)
            covered.add(stem)

    return covered


def load_treatment_goals(project_root: Path) -> list[str]:
    """Load intake goals from the treatment plan, if available.

    Args:
        project_root: Project root directory.

    Returns:
        List of goal strings (may be empty if no treatment plan exists).
    """
    plan_path = project_root / "config" / "treatment_plan.yaml"
    if not plan_path.exists():
        return []
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = yaml.safe_load(f) or {}
    return plan.get("intake_goals", [])


def score_topic_priority(
    topic_key: str,
    topic_data: dict,
    treatment_goals: list[str],
) -> int:
    """Score a topic's priority for podcast generation.

    Required topics score highest. Topics mentioned in treatment goals score
    higher than others.

    Args:
        topic_key: The topic key (e.g., 'anxiety_ocd').
        topic_data: Topic metadata from source library.
        treatment_goals: User's treatment goals from treatment_plan.yaml.

    Returns:
        Priority score — higher is more important.
    """
    score = 0

    if topic_data.get("required", False):
        score += 100

    # Check if topic's display name or key appears in treatment goals
    display_name = topic_data.get("display_name", "").lower()
    key_lower = topic_key.lower()
    goals_text = " ".join(treatment_goals).lower()

    if display_name in goals_text or key_lower in goals_text:
        score += 50

    # Preferred topics based on partial keyword match
    keywords = display_name.split() + key_lower.replace("_", " ").split()
    for kw in keywords:
        if len(kw) > 4 and kw in goals_text:
            score += 10
            break

    return score


def analyze_gaps(
    topics: dict[str, dict],
    covered: set[str],
    treatment_goals: list[str],
) -> list[dict]:
    """Find uncovered topics and rank them by priority.

    Args:
        topics: All topics from source library.
        covered: Set of topic keys that have been covered.
        treatment_goals: User's treatment goals.

    Returns:
        List of uncovered topic dicts sorted by priority descending.
    """
    gaps = []
    for key, data in topics.items():
        if key not in covered:
            score = score_topic_priority(key, data, treatment_goals)
            gaps.append({
                "key": key,
                "display_name": data.get("display_name", key),
                "description": data.get("description", ""),
                "required": data.get("required", False),
                "priority_score": score,
                "source_count": (
                    len(data.get("core_sources", []))
                    + len(data.get("supplemental_sources", []))
                ),
            })

    gaps.sort(key=lambda x: x["priority_score"], reverse=True)
    return gaps


def print_gaps(gaps: list[dict], covered: set[str], total: int) -> None:
    """Print the gap analysis to stdout.

    Args:
        gaps: List of uncovered topic dicts (sorted by priority).
        covered: Set of covered topic keys.
        total: Total number of topics in the library.
    """
    covered_count = total - len(gaps)
    print(f"\nPodcast Coverage: {covered_count}/{total} topics covered\n")

    if not gaps:
        print("All topics have been covered. Great work!")
        return

    print(f"Uncovered topics ({len(gaps)}), ranked by priority:\n")
    for i, topic in enumerate(gaps, 1):
        badge = "[required]" if topic["required"] else "          "
        print(f"  {i:>2}. {badge} {topic['display_name']}")
        if topic["description"]:
            print(f"        {topic['description']}")
        print(
            f"        Sources available: {topic['source_count']}  |  "
            f"Priority score: {topic['priority_score']}"
        )
        print()


def suggest_next(gaps: list[dict]) -> None:
    """Print a suggestion for the next podcast to generate.

    Args:
        gaps: Ranked list of uncovered topics.
    """
    if not gaps:
        return
    top = gaps[0]
    print("Suggested next topic:")
    print(f"  {top['display_name']}")
    print(f"  Key: {top['key']}")
    print("\nTo generate:")
    print(f"  python scripts/generate_podcast.py --topic \"{top['key']}\"")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze which clinical topics have not been covered by any podcast.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )
    parser.add_argument(
        "--topics-file",
        metavar="PATH",
        type=Path,
        help="Path to source_library.yaml (default: templates/source_library.yaml).",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Print the single highest-priority uncovered topic and generation command.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    project_root = get_project_root()

    topics_file = args.topics_file or (project_root / "templates" / "source_library.yaml")
    if not topics_file.exists():
        print(f"Topics file not found: {topics_file}", file=sys.stderr)
        sys.exit(1)

    topics = load_topics(topics_file)
    if not topics:
        print("No topics found in source library.", file=sys.stderr)
        sys.exit(1)

    podcasts_dir = project_root / "podcasts"
    covered = discover_covered_topics(podcasts_dir)
    treatment_goals = load_treatment_goals(project_root)

    gaps = analyze_gaps(topics, covered, treatment_goals)
    print_gaps(gaps, covered, len(topics))

    if args.suggest:
        suggest_next(gaps)

    sys.exit(0)

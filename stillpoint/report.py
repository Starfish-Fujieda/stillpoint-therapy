"""Session report generation for Stillpoint.

Produces structured markdown reports suitable for sharing with a human therapist.
Generated locally; never transmitted automatically.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from stillpoint.config import get_config_dir, get_project_root, load_config, save_config
from stillpoint.llm import send_message

logger = logging.getLogger(__name__)

# Therapist-facing report: raw observations only — no clinical interpretation.
# Safety (red_flags) leads. Interpretive sections live in the interpretation log.
_REPORT_SECTIONS = [
    "red_flags",
    "themes_covered",
    "goal_progress",
    "new_disclosures",
    "coping_strategies",
    "homework_assigned",
    "clients_own_words",
]

# Private interpretation log: the tool's own read, kept by the user only.
_INTERPRETATION_SECTIONS = [
    "emotional_trajectory",
    "patterns_observed",
]

_SECTION_HEADINGS = {
    "themes_covered": "Themes Covered",
    "goal_progress": "Goal Progress",
    "new_disclosures": "New Disclosures",
    "coping_strategies": "Coping Strategies Attempted",
    "emotional_trajectory": "Emotional Trajectory",
    "red_flags": "Red Flags",
    "patterns_observed": "Patterns Observed",
    "homework_assigned": "Homework / Practices Assigned",
    "clients_own_words": "Client's Own Words",
}


def _get_tool_name() -> str:
    """Return the configured persona name, for the report provenance header."""
    try:
        cfg = load_config("therapist.yaml")
        return cfg.get("therapist", {}).get("name", "the Stillpoint tool")
    except FileNotFoundError:
        return "the Stillpoint tool"


def _get_sessions_dir() -> Path:
    return get_config_dir() / "sessions"


def _get_reports_dir() -> Path:
    reports_dir = get_project_root() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def _load_last_report_timestamp() -> datetime | None:
    """Return the timestamp of the last generated report, or None."""
    try:
        data = load_config("report_log.yaml")
        ts = data.get("last_report_timestamp")
        if ts:
            return datetime.fromisoformat(ts)
    except FileNotFoundError:
        pass
    return None


def _save_last_report_timestamp(ts: datetime) -> None:
    """Persist the timestamp of the most recently generated report."""
    try:
        data = load_config("report_log.yaml")
    except FileNotFoundError:
        data = {}
    data["last_report_timestamp"] = ts.isoformat()
    save_config("report_log.yaml", data)


def _load_session_file(session_id: str) -> dict | None:
    """Load a single session JSON file by ID."""
    path = _get_sessions_dir() / f"session_{session_id}.json"
    if not path.exists():
        logger.warning("Session file not found: %s", path)
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_sessions_since(since: datetime | None) -> list[dict]:
    """Return all session dicts saved after `since`, or all if since is None."""
    index_path = _get_sessions_dir() / "index.json"
    if not index_path.exists():
        return []

    with open(index_path, "r", encoding="utf-8") as f:
        index: list[dict] = json.load(f)

    sessions = []
    for entry in index:
        if since is not None:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts <= since:
                continue
        data = _load_session_file(entry["id"])
        if data:
            sessions.append(data)
    return sessions


def _load_sessions_by_ids(session_ids: list[str]) -> list[dict]:
    """Load specific sessions by ID list."""
    sessions = []
    for sid in session_ids:
        data = _load_session_file(sid)
        if data:
            sessions.append(data)
    return sessions


def _anonymize_text(text: str) -> str:
    """Strip identifiable markers using the LLM."""
    system = (
        "You are a privacy filter. Rewrite the following text so that all proper names "
        "(people, places, organisations) are replaced with generic placeholders like "
        "[Person A], [Location], [Organisation]. Do not change any other content."
    )
    messages = [{"role": "user", "content": text}]
    try:
        return send_message(system, messages)
    except Exception as e:
        logger.error("Anonymization failed: %s", e)
        return text


def _build_analysis_prompt(
    sessions: list[dict],
    section: str,
    include_quotes: bool,
) -> str:
    """Return the LLM prompt for a single report section."""
    combined = "\n\n---\n\n".join(
        f"Session {i + 1} ({s.get('timestamp', 'unknown date')}):\n{s.get('content', '')}"
        for i, s in enumerate(sessions)
    )
    section_instructions = {
        "themes_covered": (
            "List the main therapeutic themes explored across these sessions. "
            "Use brief bullet points."
        ),
        "goal_progress": (
            "Describe movement on any stated treatment goals. "
            "Note progress, stagnation, or setbacks."
        ),
        "new_disclosures": (
            "Identify anything the client raised for the first time — new topics, "
            "memories, or concerns not mentioned in earlier sessions."
        ),
        "coping_strategies": (
            "List coping strategies or techniques that were tried. "
            "Note what worked and what did not."
        ),
        "emotional_trajectory": (
            "Describe the emotional arc across these sessions — improving, stable, "
            "declining, or mixed. Cite specific shifts."
        ),
        "red_flags": (
            "Flag any crisis language, escalation, new risky behaviours, or safety "
            "concerns. If none, respond with exactly: None identified."
        ),
        "patterns_observed": (
            "Describe recurring themes, avoidance patterns, defensive moves, or "
            "notable breakthroughs observed across sessions."
        ),
        "homework_assigned": (
            "List any between-session practices, exercises, or homework suggested "
            "during these sessions."
        ),
        "clients_own_words": (
            "Extract 3–5 verbatim or near-verbatim quotes from the client that "
            "capture their experience most vividly."
            + (" Use [quoted text] formatting." if include_quotes else "")
        ),
    }

    instruction = section_instructions.get(section, "Summarise this section.")
    return (
        f"You are a clinical documentation assistant. "
        f"Based on the following therapy session notes, {instruction}\n\n"
        f"Session notes:\n\n{combined}"
    )


def _generate_section(
    sessions: list[dict],
    section: str,
    include_quotes: bool = True,
) -> str:
    """Generate the content for one report section via the LLM."""
    prompt = _build_analysis_prompt(sessions, section, include_quotes)
    messages = [{"role": "user", "content": prompt}]
    system = (
        "You are a clinical documentation assistant helping a therapist understand "
        "a client's progress. Be concise, clinically precise, and non-judgmental."
    )
    try:
        return send_message(system, messages)
    except Exception as e:
        logger.error("Failed to generate section '%s': %s", section, e)
        return "_[Section unavailable due to a generation error.]_"


def _assemble_report(
    sections: dict[str, str],
    session_count: int,
    date_range: tuple[str, str],
    enabled_sections: list[str],
    tool_name: str,
) -> str:
    """Assemble the final markdown report string."""
    start_date, end_date = date_range
    now = datetime.now().strftime("%Y-%m-%d")

    frontmatter = (
        "---\n"
        f"report_date: {now}\n"
        f"session_count: {session_count}\n"
        f"period_start: {start_date}\n"
        f"period_end: {end_date}\n"
        f"generated_by: stillpoint\n"
        "---\n\n"
    )

    heading = f"# Stillpoint Session Report\n\n**Report date:** {now}  \n"
    heading += f"**Sessions covered:** {session_count}  \n"
    heading += f"**Period:** {start_date} to {end_date}\n\n"

    provenance = (
        f"> **Provenance.** Generated by Stillpoint, an AI-assisted self-therapy "
        f"tool (persona: {tool_name}). This report contains raw observations of "
        f"the client's between-session self-therapy — no clinical interpretation. "
        f"Treat it as client-reported material.\n\n---\n\n"
    )
    heading += provenance

    body_parts = []
    for key in enabled_sections:
        if key not in sections:
            continue
        heading_text = _SECTION_HEADINGS.get(key, key.replace("_", " ").title())
        content = sections[key].strip()
        body_parts.append(f"## {heading_text}\n\n{content}\n")

    footer = (
        "\n---\n\n"
        "_This report was generated locally by Stillpoint. "
        "It has not been transmitted. Review before sharing._\n"
    )

    return frontmatter + heading + "\n\n".join(body_parts) + footer


def generate_session_report(
    sessions: list[str] | None = None,
    enabled_sections: list[str] | None = None,
    anonymize: bool = False,
    save_to_disk: bool = True,
) -> str:
    """Generate a structured markdown report from session data.

    Args:
        sessions: List of session IDs to include. If None, uses all sessions
            since the last report (or all sessions if no prior report exists).
        enabled_sections: Which sections to include. Defaults to the raw
            therapist-facing sections. Valid keys: red_flags, themes_covered,
            goal_progress, new_disclosures, coping_strategies, homework_assigned,
            clients_own_words. The interpretive sections (emotional_trajectory,
            patterns_observed) are not part of this report — see
            generate_interpretation_log().
        anonymize: If True, strip identifying names/places from the report.
        save_to_disk: If True, write the report to the reports/ directory
            and update the last-report timestamp.

    Returns:
        The complete report as a markdown string.

    Raises:
        ValueError: If no sessions are found for the requested period.
    """
    if enabled_sections is None:
        enabled_sections = list(_REPORT_SECTIONS)

    # Load session data
    if sessions is not None:
        session_data = _load_sessions_by_ids(sessions)
    else:
        last_ts = _load_last_report_timestamp()
        session_data = _load_sessions_since(last_ts)

    if not session_data:
        raise ValueError("No sessions found for the requested period.")

    # Determine date range
    timestamps = [s.get("timestamp", "") for s in session_data if s.get("timestamp")]
    timestamps_sorted = sorted(timestamps)
    start_date = timestamps_sorted[0][:10] if timestamps_sorted else "unknown"
    end_date = timestamps_sorted[-1][:10] if timestamps_sorted else "unknown"

    # Generate each section
    include_quotes = "clients_own_words" in enabled_sections
    generated: dict[str, str] = {}
    for section in enabled_sections:
        if section not in _SECTION_HEADINGS:
            logger.warning("Unknown section '%s', skipping", section)
            continue
        generated[section] = _generate_section(session_data, section, include_quotes)

    # Anonymize if requested
    if anonymize:
        generated = {k: _anonymize_text(v) for k, v in generated.items()}

    report = _assemble_report(
        sections=generated,
        session_count=len(session_data),
        date_range=(start_date, end_date),
        enabled_sections=enabled_sections,
        tool_name=_get_tool_name(),
    )

    if save_to_disk:
        report_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = _get_reports_dir() / report_filename
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Report saved to %s", report_path)
        _save_last_report_timestamp(datetime.now())

    return report


def _assemble_interpretation_log(
    sections: dict[str, str],
    session_count: int,
    date_range: tuple[str, str],
) -> str:
    """Assemble the private interpretation log markdown string."""
    start_date, end_date = date_range
    now = datetime.now().strftime("%Y-%m-%d")

    parts = [
        "# Stillpoint Interpretation Log\n",
        f"**Generated:** {now}  ",
        f"**Sessions covered:** {session_count}  ",
        f"**Period:** {start_date} to {end_date}\n",
        "> **Not for your therapist.** This is Stillpoint's own interpretation of "
        "your recent sessions — the emotional trajectory and patterns it thinks it "
        "sees. It is a private record for you. Hold it against what your human "
        "therapist observes; where the two diverge, that gap is worth bringing "
        "back as a correction to how this tool is prompted.\n",
        "---\n",
    ]
    for key in _INTERPRETATION_SECTIONS:
        heading_text = _SECTION_HEADINGS.get(key, key.replace("_", " ").title())
        content = sections.get(key, "").strip()
        parts.append(f"## {heading_text}\n\n{content}\n")

    parts.append(
        "\n---\n\n"
        "_This is interpretation, not raw data and not a clinical opinion. "
        "Keep it for yourself — do not hand it to your therapist as a report._\n"
    )
    return "\n".join(parts)


def generate_interpretation_log(
    sessions: list[str] | None = None,
    save_to_disk: bool = True,
) -> str:
    """Generate the tool's private interpretation of recent sessions.

    Unlike generate_session_report() — which contains raw observations only —
    this artifact holds the tool's *interpretation*: emotional trajectory and
    observed patterns. It is intended to stay with the user as a private record
    they can hold against what their human therapist observes, and use to
    correct the tool's prompts when the two diverge. It is NOT for the human
    therapist.

    Args:
        sessions: List of session IDs to include. If None, uses all sessions
            since the last report.
        save_to_disk: If True, write the log to the reports/ directory. The
            last-report timestamp is left untouched (only generate_session_report
            advances it), so generating this log does not consume the window.

    Returns:
        The complete interpretation log as a markdown string.

    Raises:
        ValueError: If no sessions are found for the requested period.
    """
    if sessions is not None:
        session_data = _load_sessions_by_ids(sessions)
    else:
        last_ts = _load_last_report_timestamp()
        session_data = _load_sessions_since(last_ts)

    if not session_data:
        raise ValueError("No sessions found for the requested period.")

    timestamps = sorted(
        s.get("timestamp", "") for s in session_data if s.get("timestamp")
    )
    start_date = timestamps[0][:10] if timestamps else "unknown"
    end_date = timestamps[-1][:10] if timestamps else "unknown"

    generated: dict[str, str] = {}
    for section in _INTERPRETATION_SECTIONS:
        generated[section] = _generate_section(
            session_data, section, include_quotes=False
        )

    log = _assemble_interpretation_log(
        sections=generated,
        session_count=len(session_data),
        date_range=(start_date, end_date),
    )

    if save_to_disk:
        log_filename = f"interpretation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        log_path = _get_reports_dir() / log_filename
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(log)
        logger.info("Interpretation log saved to %s", log_path)

    return log

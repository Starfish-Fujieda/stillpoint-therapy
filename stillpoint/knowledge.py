"""NotebookLM interface for clinical knowledge grounding.

Shells out to the `notebooklm ask` CLI to ground therapist responses in
curated clinical literature. Returns `[UNGROUNDED]` on all failures after
up to 3 retries.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from subprocess import TimeoutExpired

from stillpoint.config import get_notebooklm_bin, load_config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 60


def _notebooklm_bin() -> str:
    """Return path to the notebooklm CLI, or raise if not found.

    Resolution order:
    1. ``STILLPOINT_NOTEBOOKLM_BIN`` environment variable
    2. PATH
    """
    env_bin = get_notebooklm_bin()
    if env_bin:
        return env_bin
    binary = shutil.which("notebooklm")
    if binary is None:
        raise RuntimeError(
            "notebooklm CLI not found in PATH. "
            "Run scripts/setup.sh to install it via pipx, "
            "or set STILLPOINT_NOTEBOOKLM_BIN to its full path."
        )
    return binary


def get_available_notebooks() -> list[dict]:
    """Return the list of configured notebooks from therapist config.

    Returns:
        List of notebook dicts with topic, notebook_id, and when_to_query.
    """
    try:
        config = load_config("therapist.yaml")
        return config.get("therapist", {}).get("notebooks", [])
    except FileNotFoundError:
        return []


def get_grounding_status() -> dict:
    """Return the current grounding status for the UI status indicator.

    Returns:
        Dict with:
        - ``notebook_count``: number of configured notebooks with
          non-empty ``notebook_id``
        - ``static_topics``: list of loaded static KB topic keys
          (empty if static KB is disabled or has no content)
        - ``static_available``: True if the static KB is enabled and
          has loaded content
    """
    notebooks = get_available_notebooks()
    notebook_count = sum(
        1 for nb in notebooks
        if nb.get("notebook_id", "").strip()
    )
    if _static_kb_enabled():
        static_kb = _load_static_knowledge()
        static_topics = list(static_kb.keys())
        static_available = bool(static_kb)
    else:
        static_topics = []
        static_available = False
    return {
        "notebook_count": notebook_count,
        "static_topics": static_topics,
        "static_available": static_available,
    }


def select_relevant_notebooks(question: str) -> list[dict]:
    """Return notebooks whose when_to_query keywords match the question.

    Falls back to all notebooks when no keywords match.

    Args:
        question: The clinical question or user message.

    Returns:
        Matched notebook dicts; the full list if nothing matches.
    """
    notebooks = get_available_notebooks()
    if not notebooks:
        return []
    question_lower = question.lower()
    matched = [
        nb for nb in notebooks
        if any(
            kw.strip() and kw.strip() in question_lower
            for kw in nb.get("when_to_query", "").lower().split(",")
        )
    ]
    return matched if matched else notebooks


def _ask_notebook(notebook_id: str, question: str) -> str:
    """Query one notebook via the CLI, retrying on timeout.

    Args:
        notebook_id: The NotebookLM notebook ID.
        question: The question to ask.

    Returns:
        Plain-text answer from the notebook, or `[UNGROUNDED]` on failure.
    """
    cmd = [_notebooklm_bin(), "ask", "-n", notebook_id, question]
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
            )
            if result.returncode == 0:
                answer = result.stdout.strip()
                if answer:
                    return answer
            logger.warning(
                "notebooklm ask returned code %d (attempt %d/%d): %s",
                result.returncode,
                attempt,
                _MAX_RETRIES,
                result.stderr.strip(),
            )
        except TimeoutExpired:
            logger.warning(
                "notebooklm ask timed out after %ds (attempt %d/%d)",
                _TIMEOUT_SECONDS,
                attempt,
                _MAX_RETRIES,
            )
    return "[UNGROUNDED]"


def query_knowledge(question: str, topics: list[str] | None = None) -> str:
    """Query NotebookLM notebooks for clinical grounding.

    Selects relevant notebooks by matching when_to_query keywords against
    the question, then queries each one. Responses are joined with blank
    lines when multiple notebooks match. If all NotebookLM queries fail
    (no binary, no notebooks, or all notebooks fail), falls back to the
    static knowledge base loaded from ``data/knowledge/``. The static KB
    can be disabled with ``STILLPOINT_STATIC_KB=false``.

    Args:
        question: The clinical question to ground.
        topics: Unused in v2 (reserved for future topic-key filtering).

    Returns:
        Grounded response text (from NotebookLM or the static KB), or
        ``[UNGROUNDED]`` if neither source can answer.
    """
    try:
        _binary = _notebooklm_bin()
    except RuntimeError as exc:
        logger.warning("Knowledge grounding skipped: %s", exc)
        static = _try_static_kb(question)
        return static if static else "[UNGROUNDED]"

    notebooks = select_relevant_notebooks(question)
    if not notebooks:
        static = _try_static_kb(question)
        return static if static else "[UNGROUNDED — no notebooks configured]"

    responses: list[str] = []
    for nb in notebooks:
        notebook_id = nb.get("notebook_id", "").strip()
        if not notebook_id:
            logger.warning("Skipping notebook '%s': no notebook_id set", nb.get("topic", "?"))
            continue
        answer = _ask_notebook(notebook_id, question)
        if answer != "[UNGROUNDED]":
            responses.append(answer)

    if not responses:
        static = _try_static_kb(question)
        return static if static else "[UNGROUNDED]"

    return "\n\n".join(responses)


# ---- Static knowledge base fallback ----------------------------------------

def _static_kb_enabled() -> bool:
    """Return True unless ``STILLPOINT_STATIC_KB`` is set to a falsy value.

    Default is enabled. Recognized falsy values (case-insensitive):
    ``false``, ``0``, ``no``, ``off``.
    """
    flag = os.environ.get("STILLPOINT_STATIC_KB", "true").lower()
    return flag not in ("false", "0", "no", "off")


def _load_static_knowledge() -> dict[str, str]:
    """Load static knowledge base from ``data/knowledge/``.

    Each ``.md`` file (except ``README.md``) is loaded as a topic. The
    topic key is the file's stem (e.g., ``act_basics`` for
    ``act_basics.md``).

    Returns:
        Dict mapping topic key to file content. Empty if the directory
        does not exist or contains no ``.md`` files.
    """
    knowledge_dir = Path(__file__).resolve().parent.parent / "data" / "knowledge"
    if not knowledge_dir.exists():
        return {}
    topics: dict[str, str] = {}
    for md_file in sorted(knowledge_dir.glob("*.md")):
        if md_file.name == "README.md":
            continue
        topic_key = md_file.stem
        try:
            topics[topic_key] = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to load static KB file %s: %s", md_file, exc)
    return topics


def _extract_keywords(content: str) -> list[str]:
    """Extract keywords from a markdown file's ``keywords:`` line.

    Looks for a line starting with ``keywords:`` in the first 50 lines
    of the file. Returns lowercase keywords. Empty if not found.
    """
    for line in content.split("\n")[:50]:
        stripped = line.strip().lower()
        if stripped.startswith("keywords:"):
            kw_str = line.split(":", 1)[1].strip()
            return [k.strip().lower() for k in kw_str.split(",") if k.strip()]
    return []


def _query_static_knowledge(
    question: str,
    static_kb: dict[str, str],
) -> str | None:
    """Score each static KB topic by keyword hits; return the best match.

    The topic with the most keyword hits in the question wins. Ties go
    to the topic that appears first in the sorted iteration order.

    Args:
        question: The clinical question to ground.
        static_kb: Dict mapping topic key to file content.

    Returns:
        Tagged fallback content (explicitly marked as a draft, not yet
        clinically reviewed) from the best-matching topic, or ``None``
        if no topic has any keyword hit.
    """
    if not static_kb:
        return None
    question_lower = question.lower()
    best_key: str | None = None
    best_score = 0
    for topic_key, content in static_kb.items():
        keywords = _extract_keywords(content)
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw in question_lower)
        if score > best_score:
            best_score = score
            best_key = topic_key
    if best_key is None:
        return None
    # Honest labeling: the shipped static KB files are drafts whose inline
    # citations are not yet verified (see ``[CITATION NEEDED]`` markers in
    # ``data/knowledge/*.md``). Until clinician/peer review resolves them, the
    # tag must NOT claim "grounded" or name a "source" (which implies a
    # verified citation). It is flagged as an unreviewed fallback so the user
    # is never misled about how much weight the content carries.
    return (
        f"[FALLBACK — draft static content, not yet clinically reviewed "
        f"(topic: {best_key})]\n\n"
        f"{static_kb[best_key]}"
    )


def _try_static_kb(question: str) -> str | None:
    """Try to ground via the static knowledge base.

    Returns tagged content if a topic matches; ``None`` if the static
    KB is disabled, has no content, or no topic matches the question.
    """
    if not _static_kb_enabled():
        return None
    static_kb = _load_static_knowledge()
    return _query_static_knowledge(question, static_kb)

"""NotebookLM interface for clinical knowledge grounding.

Shells out to the `notebooklm ask` CLI to ground therapist responses in
curated clinical literature. Returns `[UNGROUNDED]` on all failures after
up to 3 retries.
"""

import logging
import shutil
import subprocess
from subprocess import TimeoutExpired

from stillpoint.config import load_config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 60


def _notebooklm_bin() -> str:
    """Return path to the notebooklm CLI, or raise if not found."""
    binary = shutil.which("notebooklm")
    if binary is None:
        raise RuntimeError(
            "notebooklm CLI not found in PATH. "
            "Run scripts/setup.sh to install it via pipx."
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
    lines when multiple notebooks match.

    Args:
        question: The clinical question to ground.
        topics: Unused in v2 (reserved for future topic-key filtering).

    Returns:
        Grounded response text, or `[UNGROUNDED]` if all queries fail.
    """
    try:
        binary = _notebooklm_bin()
    except RuntimeError as exc:
        logger.warning("Knowledge grounding skipped: %s", exc)
        return "[UNGROUNDED]"

    notebooks = select_relevant_notebooks(question)
    if not notebooks:
        return "[UNGROUNDED — no notebooks configured]"

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
        return "[UNGROUNDED]"

    return "\n\n".join(responses)

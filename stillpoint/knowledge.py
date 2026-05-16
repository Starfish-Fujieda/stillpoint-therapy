"""NotebookLM interface for clinical knowledge grounding.

MVP: Returns a stub response indicating the knowledge base is not yet connected.
Full implementation will shell out to the notebooklm CLI.
"""

from stillpoint.config import load_config


def query_knowledge(question: str, topics: list[str] | None = None) -> str:
    """Query NotebookLM notebooks for clinical grounding.

    Args:
        question: The clinical question to ground.
        topics: Optional list of topic keys to narrow the query.

    Returns:
        A grounded response from the knowledge base, or an [UNGROUNDED] marker.
    """
    try:
        config = load_config("therapist.yaml")
        notebooks = config.get("therapist", {}).get("notebooks", [])
        if not notebooks:
            return "[UNGROUNDED — no notebooks configured]"
    except FileNotFoundError:
        return "[UNGROUNDED — therapist config not found]"

    # TODO: Full implementation — shell out to `notebooklm ask` CLI
    # For MVP, return a note that knowledge grounding is not yet active
    return "[UNGROUNDED — NotebookLM integration pending. Respond from persona training.]"


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


def select_relevant_notebooks(question: str) -> list[str]:
    """Match a question to relevant notebook topic keys.

    Args:
        question: The user's message or a derived clinical question.

    Returns:
        List of topic keys that may be relevant.
    """
    notebooks = get_available_notebooks()
    relevant = []
    question_lower = question.lower()
    for nb in notebooks:
        trigger = nb.get("when_to_query", "").lower()
        # Simple keyword matching for MVP
        keywords = [k.strip() for k in trigger.split(",")]
        if any(kw in question_lower for kw in keywords if kw):
            relevant.append(nb.get("topic", ""))
    return relevant
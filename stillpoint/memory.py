"""Session memory interface for Stillpoint.

MVP: Uses simple JSON file-based storage for session notes.
Full implementation will use MemPalace + ChromaDB vector store.
"""

import json
from datetime import datetime
from pathlib import Path

from stillpoint.config import get_project_root


def _get_memory_dir() -> Path:
    """Return the memory storage directory, creating it if needed."""
    memory_dir = get_project_root() / "config" / "sessions"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def _get_session_index() -> list[dict]:
    """Load the session index (list of session metadata)."""
    index_path = _get_memory_dir() / "index.json"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_session_index(index: list[dict]) -> None:
    """Save the session index."""
    index_path = _get_memory_dir() / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def save_session_notes(content: str) -> bool:
    """Save session notes to file-based storage.

    Args:
        content: The session notes text to save.

    Returns:
        True if saved successfully.
    """
    now = datetime.now()
    session_id = now.strftime("%Y%m%d_%H%M%S")

    # Save individual session file
    session_path = _get_memory_dir() / f"session_{session_id}.json"
    session_data = {
        "id": session_id,
        "timestamp": now.isoformat(),
        "content": content,
    }
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    # Update index
    index = _get_session_index()
    index.append({
        "id": session_id,
        "timestamp": now.isoformat(),
        "preview": content[:200],
    })
    _save_session_index(index)
    return True


def search_sessions(query: str, results: int = 20) -> list[str]:
    """Simple text search across past sessions.

    Args:
        query: Search query string.
        results: Maximum number of results to return.

    Returns:
        List of session content strings matching the query.
    """
    # TODO: Full implementation with ChromaDB semantic search
    index = _get_session_index()
    query_lower = query.lower()
    matching = []

    for entry in index[-results:]:
        session_path = _get_memory_dir() / f"session_{entry['id']}.json"
        if session_path.exists():
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                content = data.get("content", "")
                if query_lower in content.lower():
                    matching.append(content)

    return matching


def get_recent_sessions(count: int = 3) -> list[str]:
    """Get the most recent session notes.

    Args:
        count: Number of recent sessions to retrieve.

    Returns:
        List of session content strings, most recent last.
    """
    index = _get_session_index()
    recent = index[-count:] if len(index) >= count else index
    sessions = []

    for entry in recent:
        session_path = _get_memory_dir() / f"session_{entry['id']}.json"
        if session_path.exists():
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append(data.get("content", ""))

    return sessions


def get_wake_up_context() -> str:
    """Get condensed context for session start.

    Returns:
        A summary string of recent sessions and key context.
    """
    count = get_session_count()
    if count == 0:
        return "This is the first session."

    recent = get_recent_sessions(3)
    context_parts = [f"Total sessions: {count}"]
    if recent:
        context_parts.append("Recent session summaries:")
        for i, session in enumerate(recent, 1):
            preview = session[:300] + ("..." if len(session) > 300 else "")
            context_parts.append(f"  Session -{len(recent) - i + 1}: {preview}")

    return "\n".join(context_parts)


def get_session_count() -> int:
    """Return total number of stored sessions."""
    return len(_get_session_index())
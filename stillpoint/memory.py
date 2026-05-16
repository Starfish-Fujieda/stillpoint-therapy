"""Session memory interface for Stillpoint.

Uses ChromaDB for semantic vector search with JSON file fallback.
If ChromaDB is not installed, falls back to file-based text search.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from stillpoint.config import get_project_root

# Attempt ChromaDB import; degrade gracefully if not installed.
try:
    import chromadb

    _CHROMADB_AVAILABLE = True
except ImportError:
    _CHROMADB_AVAILABLE = False


# Module-level cache for the ChromaDB client and collection.
_chroma_client: Optional[object] = None
_chroma_collection: Optional[object] = None
_chroma_path: Optional[str] = None


def _get_memory_dir() -> Path:
    """Return the memory storage directory, creating it if needed."""
    memory_dir = get_project_root() / "config" / "sessions"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def _get_chroma_dir() -> Path:
    """Return the ChromaDB persistence directory, creating it if needed."""
    chroma_dir = get_project_root() / "data" / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


def _get_collection():
    """Return the ChromaDB collection, initialising client on first call."""
    global _chroma_client, _chroma_collection, _chroma_path

    if not _CHROMADB_AVAILABLE:
        return None

    # Re-initialise if the storage path has changed (e.g. between tests).
    expected_path = str(_get_chroma_dir())
    if _chroma_path != expected_path:
        _chroma_client = None
        _chroma_collection = None

    if _chroma_client is None:
        try:
            _chroma_client = chromadb.PersistentClient(path=expected_path)
            _chroma_path = expected_path
            _chroma_collection = _chroma_client.get_or_create_collection("sessions")
        except Exception:
            _chroma_client = None
            _chroma_collection = None
            _chroma_path = None

    return _chroma_collection


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


def _text_search(query: str, results: int) -> list[str]:
    """Naive case-insensitive text search across JSON session files."""
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


def save_session_notes(content: str) -> bool:
    """Save session notes to JSON storage and ChromaDB.

    Args:
        content: The session notes text to save.

    Returns:
        True if saved successfully.
    """
    now = datetime.now()
    session_id = now.strftime("%Y%m%d_%H%M%S")

    # Save individual JSON session file (always — acts as durable fallback).
    session_path = _get_memory_dir() / f"session_{session_id}.json"
    session_data = {
        "id": session_id,
        "timestamp": now.isoformat(),
        "content": content,
    }
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    # Update JSON index.
    index = _get_session_index()
    index.append({
        "id": session_id,
        "timestamp": now.isoformat(),
        "preview": content[:200],
    })
    _save_session_index(index)

    # Also store in ChromaDB for semantic search.
    collection = _get_collection()
    if collection is not None:
        try:
            collection.add(
                documents=[content],
                ids=[session_id],
                metadatas=[{"timestamp": now.isoformat(), "session_id": session_id}],
            )
        except Exception:
            pass  # ChromaDB failure is non-fatal; JSON is the source of truth.

    return True


def search_sessions(query: str, results: int = 20) -> list[str]:
    """Semantic search across past sessions via ChromaDB.

    Falls back to case-insensitive text search when ChromaDB is unavailable
    or returns no results (e.g. sessions indexed only in JSON).

    Args:
        query: Search query string.
        results: Maximum number of results to return.

    Returns:
        List of session content strings matching the query.
    """
    collection = _get_collection()
    if collection is not None:
        try:
            total = collection.count()
            if total > 0:
                n = min(results, total)
                response = collection.query(query_texts=[query], n_results=n)
                docs = response.get("documents", [[]])[0]
                if docs:
                    return docs
        except Exception:
            pass  # Fall through to text search.

    # Fallback: plain text search over JSON files.
    return _text_search(query, results)


def get_recent_sessions(count: int = 3) -> list[str]:
    """Get the most recent session notes.

    Uses the JSON index for reliable recency ordering (ChromaDB metadata
    ordering is not guaranteed).

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

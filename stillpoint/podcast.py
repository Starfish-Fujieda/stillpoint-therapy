"""Podcast generation for Stillpoint.

Primary path: NotebookLM Audio Overview via the notebooklm CLI (pipx).
Secondary path: local TTS via Podcastfy — not yet implemented (v2).
"""

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from stillpoint.config import get_project_root, load_config

logger = logging.getLogger(__name__)


def _get_podcasts_dir() -> Path:
    """Return the podcasts output directory, creating it if needed."""
    podcasts_dir = get_project_root() / "podcasts"
    podcasts_dir.mkdir(parents=True, exist_ok=True)
    return podcasts_dir


def _get_notebooks() -> list[dict]:
    """Return configured notebooks from therapist config."""
    try:
        config = load_config("therapist.yaml")
        return config.get("therapist", {}).get("notebooks", [])
    except FileNotFoundError:
        return []


def _select_notebook(topic: str | None) -> dict | None:
    """Pick the most relevant notebook for the given topic.

    If topic is None, return the first configured notebook.
    """
    notebooks = _get_notebooks()
    if not notebooks:
        return None
    if topic is None:
        return notebooks[0]
    topic_lower = topic.lower()
    for nb in notebooks:
        trigger = nb.get("when_to_query", "").lower()
        keywords = [k.strip() for k in trigger.split(",")]
        if any(kw and kw in topic_lower for kw in keywords):
            return nb
    return notebooks[0]


def _notebooklm_bin() -> str:
    """Return path to the notebooklm CLI, or raise if not found."""
    binary = shutil.which("notebooklm")
    if binary is None:
        raise RuntimeError(
            "notebooklm CLI not found in PATH. "
            "Run scripts/setup.sh to install it via pipx."
        )
    return binary


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a notebooklm subcommand and return the result."""
    cmd = [_notebooklm_bin()] + args
    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def generate_podcast(topic: str | None = None, method: str = "notebooklm") -> str:
    """Generate a therapy podcast episode.

    Args:
        topic: Topic to generate about. If None, uses the first configured notebook.
        method: "notebooklm" (Audio Overview via CLI) or "local" (Podcastfy — not implemented).

    Returns:
        Absolute path to the generated audio file.

    Raises:
        ValueError: If method is unknown.
        NotImplementedError: If method is "local".
        RuntimeError: If the notebooklm CLI is unavailable or generation fails.
    """
    if method == "local":
        raise NotImplementedError(
            "Local TTS via Podcastfy is a v2 feature and not yet implemented."
        )
    if method != "notebooklm":
        raise ValueError(f"Unknown method: {method!r}. Use 'notebooklm' or 'local'.")

    notebook = _select_notebook(topic)
    if notebook is None:
        raise RuntimeError(
            "No notebooks configured. Complete onboarding and add notebook IDs to config/therapist.yaml."
        )

    notebook_id = notebook.get("notebook_id", "").strip()
    if not notebook_id:
        raise RuntimeError(
            f"Notebook '{notebook.get('topic')}' has no notebook_id set. "
            "Open NotebookLM, copy the notebook ID from the URL, and add it to config/therapist.yaml."
        )

    topic_label = topic or notebook.get("topic", "therapy")
    instructions = f"Focus on {topic_label}" if topic else ""

    # Trigger generation — returns task_id immediately
    gen_args = ["generate", "audio", "--notebook", notebook_id, "--json"]
    if instructions:
        gen_args.append(instructions)

    result = _run(gen_args, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"notebooklm generate audio failed: {result.stderr.strip()}")

    try:
        gen_data = json.loads(result.stdout.strip())
        artifact_id = gen_data.get("task_id") or gen_data.get("artifact_id", "")
    except (json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError(
            f"Unexpected output from notebooklm generate audio: {result.stdout!r}"
        ) from exc

    # Wait for completion (audio takes 10-20 min; use a long timeout)
    wait_result = _run(
        ["artifact", "wait", artifact_id, "-n", notebook_id, "--timeout", "1200"],
        timeout=1250,
    )
    if wait_result.returncode == 2:
        raise RuntimeError(
            f"Timed out waiting for audio artifact {artifact_id}. "
            "Check status with: notebooklm artifact list"
        )
    if wait_result.returncode != 0:
        raise RuntimeError(
            f"Error waiting for artifact: {wait_result.stderr.strip()}"
        )

    # Download to podcasts/
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic_label)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_label}.mp3"
    output_path = _get_podcasts_dir() / filename

    dl_result = _run(
        ["download", "audio", str(output_path), "-a", artifact_id, "-n", notebook_id],
        timeout=120,
    )
    if dl_result.returncode != 0:
        raise RuntimeError(f"notebooklm download audio failed: {dl_result.stderr.strip()}")

    logger.info("Podcast saved to %s", output_path)
    return str(output_path)


def list_generated_podcasts() -> list[dict]:
    """Return metadata for all generated podcasts in the podcasts/ directory.

    Returns:
        List of dicts with keys: filename, path, size_bytes, created_at (ISO 8601).
        Sorted newest-first.
    """
    podcasts_dir = _get_podcasts_dir()
    entries = []
    for mp3 in sorted(podcasts_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = mp3.stat()
        entries.append({
            "filename": mp3.name,
            "path": str(mp3),
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return entries

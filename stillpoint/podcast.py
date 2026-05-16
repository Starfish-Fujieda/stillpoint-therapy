"""Podcast generation for Stillpoint.

Primary path: NotebookLM Audio Overview via the notebooklm CLI (pipx).
Secondary path: local TTS via Podcastfy / pyttsx3 / gTTS (v2).
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


def _generate_local_podcast(topic: str | None, output_dir: Path) -> str:
    """Try each available TTS engine in order and return the output file path.

    Preference order: podcastfy (best quality) > pyttsx3 (offline) > gtts (online).

    Raises:
        RuntimeError: When no TTS engine is installed.
    """
    from stillpoint.memory import get_recent_sessions

    topic_label = topic or "therapy"
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic_label)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sessions = get_recent_sessions(3)
    content = f"Therapy podcast on {topic_label}.\n\n" + "\n\n".join(sessions)

    # --- podcastfy (best quality, podcast-style dialogue) ---
    try:
        import podcastfy  # type: ignore[import]

        filename = f"{timestamp}_{safe_label}_local.mp3"
        output_path = output_dir / filename
        podcastfy.generate(text=content, output=str(output_path))
        logger.info("Podcast saved via podcastfy to %s", output_path)
        return str(output_path)
    except ImportError:
        pass

    # --- pyttsx3 (offline TTS, produces .wav) ---
    try:
        import pyttsx3  # type: ignore[import]

        filename = f"{timestamp}_{safe_label}_local.wav"
        output_path = output_dir / filename
        engine = pyttsx3.init()
        engine.save_to_file(content, str(output_path))
        engine.runAndWait()
        logger.info("Podcast saved via pyttsx3 to %s", output_path)
        return str(output_path)
    except ImportError:
        pass

    # --- gtts (Google TTS, requires internet) ---
    try:
        from gtts import gTTS  # type: ignore[import]

        filename = f"{timestamp}_{safe_label}_local.mp3"
        output_path = output_dir / filename
        tts = gTTS(text=content, lang="en")
        tts.save(str(output_path))
        logger.info("Podcast saved via gTTS to %s", output_path)
        return str(output_path)
    except ImportError:
        pass

    raise RuntimeError(
        "No TTS engine available for local podcast generation. "
        "Install one of: podcastfy, pyttsx3, or gtts.\n"
        "  pip install podcastfy   # Best quality, podcast-style dialogue\n"
        "  pip install pyttsx3     # Offline TTS\n"
        "  pip install gtts        # Google TTS (requires internet)"
    )


def generate_podcast(topic: str | None = None, method: str = "notebooklm") -> str:
    """Generate a therapy podcast episode.

    Args:
        topic: Topic to generate about. If None, uses the first configured notebook.
        method: "notebooklm" (Audio Overview via CLI) or "local" (podcastfy/pyttsx3/gtts).

    Returns:
        Absolute path to the generated audio file.

    Raises:
        ValueError: If method is unknown.
        RuntimeError: If the notebooklm CLI is unavailable, generation fails,
                      or no TTS engine is installed for the "local" method.
    """
    if method == "local":
        return _generate_local_podcast(topic, _get_podcasts_dir())
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

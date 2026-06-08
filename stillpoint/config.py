"""Configuration loading and saving utilities for Stillpoint."""

import os
from pathlib import Path

import yaml


# Environment variable names used for path overrides.
ENV_PALACE_PATH = "STILLPOINT_PALACE_PATH"
ENV_MEMPALACE_BIN = "STILLPOINT_MEMPALACE_BIN"
ENV_NOTEBOOKLM_BIN = "STILLPOINT_NOTEBOOKLM_BIN"


def get_project_root() -> Path:
    """Return the project root directory.

    Walks up from this file to find the directory containing config/, templates/, etc.
    """
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "templates").is_dir() and (parent / "stillpoint").is_dir():
            return parent
    # Fallback: assume standard layout
    return current.parent


def get_config_dir() -> Path:
    """Return the config directory path, creating it if needed."""
    config_dir = get_project_root() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_templates_dir() -> Path:
    """Return the templates directory path."""
    return get_project_root() / "templates"


def get_personas_dir() -> Path:
    """Return the personas directory path, creating it if needed."""
    personas_dir = get_project_root() / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)
    return personas_dir


def get_palace_dir() -> Path:
    """Return the palace directory for ChromaDB / MemPalace storage.

    Uses ``STILLPOINT_PALACE_PATH`` if set, otherwise falls back to
    ``<project_root>/data/palace``.
    """
    env_path = os.environ.get(ENV_PALACE_PATH)
    if env_path:
        palace_dir = Path(env_path).expanduser()
    else:
        palace_dir = get_project_root() / "data" / "palace"
    palace_dir.mkdir(parents=True, exist_ok=True)
    return palace_dir


def get_mempalace_bin() -> str | None:
    """Return the mempalace binary path, or None if not found.

    Uses ``STILLPOINT_MEMPALACE_BIN`` if set, otherwise searches PATH
    and the active venv's bin directory.
    """
    env_bin = os.environ.get(ENV_MEMPALACE_BIN)
    if env_bin:
        path = Path(env_bin).expanduser()
        return str(path) if path.exists() else None
    return None


def get_notebooklm_bin() -> str | None:
    """Return the notebooklm binary path, or None if not found.

    Uses ``STILLPOINT_NOTEBOOKLM_BIN`` if set, otherwise searches PATH.
    """
    env_bin = os.environ.get(ENV_NOTEBOOKLM_BIN)
    if env_bin:
        path = Path(env_bin).expanduser()
        return str(path) if path.exists() else None
    return None


def load_config(filename: str) -> dict:
    """Load a YAML config file from the config directory.

    Args:
        filename: Name of the config file (e.g., 'therapist.yaml').

    Returns:
        Parsed YAML as a dictionary.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
    """
    path = get_config_dir() / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(filename: str, data: dict) -> None:
    """Save a dictionary as a YAML config file.

    Args:
        filename: Name of the config file (e.g., 'therapist.yaml').
        data: Dictionary to serialize as YAML.
    """
    path = get_config_dir() / filename
    get_config_dir().mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def is_configured() -> bool:
    """Check if onboarding has been completed.

    Returns True if the essential config files exist.
    """
    config_dir = get_config_dir()
    required_files = ["therapist.yaml", "user_profile.yaml", "treatment_plan.yaml"]
    return all((config_dir / f).exists() for f in required_files)


def get_notebook_count() -> int:
    """Count configured notebooks with non-empty ``notebook_id``.

    Reads ``therapist.yaml`` and counts entries in
    ``therapist.notebooks`` whose ``notebook_id`` is a non-empty
    string (after stripping whitespace). Returns 0 when the config
    file is missing or no notebooks are configured.
    """
    try:
        config = load_config("therapist.yaml")
    except FileNotFoundError:
        return 0
    notebooks = config.get("therapist", {}).get("notebooks", []) or []
    return sum(
        1 for nb in notebooks
        if isinstance(nb, dict) and str(nb.get("notebook_id", "")).strip()
    )


def load_source_library() -> dict:
    """Load the source library from templates.

    Returns:
        The source library as a dictionary.
    """
    path = get_templates_dir() / "source_library.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_referral_resources() -> str:
    """Load the referral resources markdown.

    Returns:
        The referral resources as a string.
    """
    # Check project root first, then templates
    root_path = get_project_root() / "referral_resources.md"
    if root_path.exists():
        with open(root_path, "r", encoding="utf-8") as f:
            return f.read()
    template_path = get_templates_dir() / "referral_resources.md"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "No referral resources configured. Please add your local resources."
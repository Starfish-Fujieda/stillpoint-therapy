"""Shared fixtures for Stillpoint tests."""

import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def project_root(tmp_path, monkeypatch):
    """Redirect all project-root-relative I/O to a temp directory."""
    (tmp_path / "config").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "stillpoint").mkdir()
    (tmp_path / "personas").mkdir()

    monkeypatch.setattr("stillpoint.config.get_project_root", lambda: tmp_path)
    # Patch in every module that imports get_project_root directly
    for mod in (
        "stillpoint.memory",
        "stillpoint.report",
        "stillpoint.podcast",
        "stillpoint.persona",
    ):
        try:
            monkeypatch.setattr(f"{mod}.get_project_root", lambda: tmp_path)
        except AttributeError:
            pass

    return tmp_path


@pytest.fixture()
def source_library(project_root):
    """Write a minimal source_library.yaml to the temp templates dir."""
    data = {
        "topics": [
            {"id": "anxiety", "name": "Anxiety", "required": True, "sources": []},
            {"id": "depression", "name": "Depression", "required": True, "sources": []},
            {"id": "trauma", "name": "Trauma", "required": False, "sources": []},
        ]
    }
    path = project_root / "templates" / "source_library.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return data


@pytest.fixture()
def therapist_config(project_root):
    """Write a minimal therapist.yaml to the temp config dir."""
    data = {
        "therapist": {
            "name": "Dr. Test",
            "notebooks": [
                {
                    "topic": "Anxiety",
                    "notebook_id": "nb-anxiety-123",
                    "when_to_query": "anxiety, worry, panic",
                },
                {
                    "topic": "Depression",
                    "notebook_id": "nb-depression-456",
                    "when_to_query": "depression, low mood, sadness",
                },
            ],
        }
    }
    path = project_root / "config" / "therapist.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return data


@pytest.fixture()
def session_store(project_root):
    """Create a populated sessions directory with two sessions."""
    sessions_dir = project_root / "config" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    sessions = [
        {
            "id": "20240101_100000",
            "timestamp": "2024-01-01T10:00:00",
            "content": "Talked about anxiety and breathing exercises.",
        },
        {
            "id": "20240115_140000",
            "timestamp": "2024-01-15T14:00:00",
            "content": "Discussed sleep patterns and depression symptoms.",
        },
    ]
    index = []
    for s in sessions:
        (sessions_dir / f"session_{s['id']}.json").write_text(
            json.dumps(s, indent=2), encoding="utf-8"
        )
        index.append({"id": s["id"], "timestamp": s["timestamp"], "preview": s["content"][:200]})

    (sessions_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return sessions

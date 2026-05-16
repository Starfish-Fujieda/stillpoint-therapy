"""Tests for stillpoint.config."""

import pytest
import yaml

from stillpoint.config import (
    get_config_dir,
    get_project_root,
    is_configured,
    load_config,
    load_source_library,
    save_config,
)


def test_load_config_roundtrip(project_root):
    data = {"key": "value", "nested": {"a": 1}}
    save_config("test.yaml", data)
    loaded = load_config("test.yaml")
    assert loaded == data


def test_load_config_missing_raises(project_root):
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


def test_save_config_creates_file(project_root):
    save_config("newfile.yaml", {"x": 42})
    path = project_root / "config" / "newfile.yaml"
    assert path.exists()
    content = yaml.safe_load(path.read_text())
    assert content == {"x": 42}


def test_load_config_empty_file_returns_dict(project_root):
    (project_root / "config" / "empty.yaml").write_text("", encoding="utf-8")
    result = load_config("empty.yaml")
    assert result == {}


def test_is_configured_false_when_files_missing(project_root):
    assert is_configured() is False


def test_is_configured_true_when_all_files_present(project_root):
    for name in ("therapist.yaml", "user_profile.yaml", "treatment_plan.yaml"):
        save_config(name, {"ok": True})
    assert is_configured() is True


def test_is_configured_false_when_only_some_files_present(project_root):
    save_config("therapist.yaml", {})
    assert is_configured() is False


def test_load_source_library(project_root, source_library):
    result = load_source_library()
    assert "topics" in result
    assert len(result["topics"]) == 3
    assert result["topics"][0]["id"] == "anxiety"


def test_get_config_dir_creates_dir(project_root):
    config_dir = get_config_dir()
    assert config_dir.exists()
    assert config_dir.is_dir()

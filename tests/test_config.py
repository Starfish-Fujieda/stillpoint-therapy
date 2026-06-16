"""Tests for stillpoint.config."""

import pytest
import yaml

from stillpoint.config import (
    get_config_dir,
    get_notebook_count,
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


# ---------------------------------------------------------------------------
# get_notebook_count
# ---------------------------------------------------------------------------

def test_get_notebook_count_zero_when_no_config(project_root):
    """No therapist.yaml present → 0 notebooks."""
    assert get_notebook_count() == 0


def test_get_notebook_count_zero_when_no_notebooks_key(project_root):
    """therapist.yaml exists but has no 'notebooks' key → 0."""
    save_config("therapist.yaml", {"therapist": {"name": "Dr. Test"}})
    assert get_notebook_count() == 0


def test_get_notebook_count_zero_when_all_notebook_ids_blank(project_root):
    """Notebooks present but all notebook_id fields are empty → 0."""
    save_config("therapist.yaml", {
        "therapist": {
            "name": "Dr. Test",
            "notebooks": [
                {"topic": "Anxiety", "notebook_id": "", "when_to_query": "anxiety"},
                {"topic": "Depression", "notebook_id": "   ", "when_to_query": "depression"},
            ],
        }
    })
    assert get_notebook_count() == 0


def test_get_notebook_count_counts_configured(therapist_config):
    """The therapist_config fixture has 2 configured notebooks → 2."""
    assert get_notebook_count() == 2


def test_get_notebook_count_mixed_blank_and_configured(project_root):
    """Mixed list (one blank ID, one configured) → 1."""
    save_config("therapist.yaml", {
        "therapist": {
            "notebooks": [
                {"topic": "Anxiety", "notebook_id": "nb-anxiety-123"},
                {"topic": "Depression", "notebook_id": ""},
            ],
        }
    })
    assert get_notebook_count() == 1


def test_load_source_library(project_root, source_library):
    result = load_source_library()
    assert "topics" in result
    assert len(result["topics"]) == 3
    assert result["topics"][0]["id"] == "anxiety"


def test_get_config_dir_creates_dir(project_root):
    config_dir = get_config_dir()
    assert config_dir.exists()
    assert config_dir.is_dir()

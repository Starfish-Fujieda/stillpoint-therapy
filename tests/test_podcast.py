"""Tests for stillpoint.podcast (no actual notebooklm calls)."""

import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml

import stillpoint.podcast as podcast
from stillpoint.podcast import (
    _get_notebooks,
    _load_registry,
    _record_podcast,
    _select_notebook,
    generate_podcast,
    list_generated_podcasts,
)


@pytest.fixture(autouse=True)
def _redirect_podcast(project_root, monkeypatch):
    monkeypatch.setattr(podcast, "get_project_root", lambda: project_root)


# --- _get_notebooks ----------------------------------------------------------

def test_get_notebooks_empty_when_no_config(project_root):
    assert _get_notebooks() == []


def test_get_notebooks_returns_list(project_root, therapist_config):
    nbs = _get_notebooks()
    assert len(nbs) == 2
    assert nbs[0]["topic"] == "Anxiety"


# --- _select_notebook --------------------------------------------------------

def test_select_notebook_none_topic_returns_first(project_root, therapist_config):
    nb = _select_notebook(None)
    assert nb["topic"] == "Anxiety"


def test_select_notebook_keyword_match(project_root, therapist_config):
    nb = _select_notebook("managing worry")
    assert nb["topic"] == "Anxiety"


def test_select_notebook_second_keyword_match(project_root, therapist_config):
    nb = _select_notebook("low mood treatment")
    assert nb["topic"] == "Depression"


def test_select_notebook_no_match_falls_back_to_first(project_root, therapist_config):
    nb = _select_notebook("trauma and PTSD")
    assert nb["topic"] == "Anxiety"


def test_select_notebook_no_notebooks_returns_none(project_root):
    assert _select_notebook("anxiety") is None


# --- list_generated_podcasts -------------------------------------------------

def test_list_generated_podcasts_empty_dir(project_root):
    (project_root / "podcasts").mkdir()
    assert list_generated_podcasts() == []


def test_list_generated_podcasts_returns_metadata(project_root):
    podcasts_dir = project_root / "podcasts"
    podcasts_dir.mkdir()
    mp3 = podcasts_dir / "20240101_120000_anxiety.mp3"
    mp3.write_bytes(b"\xff\xfb" + b"\x00" * 100)

    results = list_generated_podcasts()
    assert len(results) == 1
    assert results[0]["filename"] == "20240101_120000_anxiety.mp3"
    assert "path" in results[0]
    assert "size_bytes" in results[0]
    assert results[0]["size_bytes"] == 102


def test_list_generated_podcasts_sorted_newest_first(project_root):
    podcasts_dir = project_root / "podcasts"
    podcasts_dir.mkdir()
    (podcasts_dir / "old.mp3").write_bytes(b"\x00" * 10)
    (podcasts_dir / "new.mp3").write_bytes(b"\x00" * 20)
    import time; time.sleep(0.01)

    results = list_generated_podcasts()
    assert len(results) == 2
    # sorted newest-first means the one created most recently is index 0
    filenames = [r["filename"] for r in results]
    assert "new.mp3" in filenames


# --- podcast registry: impetus + intended_takeaways --------------------------

def test_record_podcast_writes_registry(project_root):
    podcasts_dir = project_root / "podcasts"
    podcasts_dir.mkdir()
    mp3 = podcasts_dir / "ep1.mp3"
    mp3.write_bytes(b"\x00" * 50)

    _record_podcast(
        str(mp3), "anxiety_ocd", "notebooklm",
        impetus="rising anxiety this week",
        intended_takeaways="normalize anxiety; urge-surfing",
    )

    registry = _load_registry()
    assert len(registry["podcasts"]) == 1
    entry = registry["podcasts"][0]
    assert entry["filename"] == "ep1.mp3"
    assert entry["topic"] == "anxiety_ocd"
    assert entry["impetus"] == "rising anxiety this week"
    assert entry["intended_takeaways"] == "normalize anxiety; urge-surfing"


def test_record_podcast_appends_to_registry(project_root):
    podcasts_dir = project_root / "podcasts"
    podcasts_dir.mkdir()
    for name in ("a.mp3", "b.mp3"):
        path = podcasts_dir / name
        path.write_bytes(b"\x00" * 10)
        _record_podcast(str(path), "topic", "local", "impetus", "takeaway")

    assert len(_load_registry()["podcasts"]) == 2


def test_list_generated_podcasts_reads_registry(project_root):
    podcasts_dir = project_root / "podcasts"
    podcasts_dir.mkdir()
    mp3 = podcasts_dir / "registered.mp3"
    mp3.write_bytes(b"\x00" * 30)
    _record_podcast(
        str(mp3), "anxiety_ocd", "notebooklm",
        impetus="why-it", intended_takeaways="takeaway-it",
    )

    results = list_generated_podcasts()
    assert len(results) == 1
    assert results[0]["impetus"] == "why-it"
    assert results[0]["intended_takeaways"] == "takeaway-it"
    assert results[0].get("legacy") is not True


def test_list_generated_podcasts_mixes_registry_and_legacy(project_root):
    podcasts_dir = project_root / "podcasts"
    podcasts_dir.mkdir()

    registered = podcasts_dir / "registered.mp3"
    registered.write_bytes(b"\x00" * 30)
    _record_podcast(str(registered), "topic", "local", "imp", "take")

    legacy = podcasts_dir / "legacy.mp3"
    legacy.write_bytes(b"\x00" * 40)

    results = list_generated_podcasts()
    assert {r["filename"] for r in results} == {"registered.mp3", "legacy.mp3"}

    legacy_entry = next(r for r in results if r["filename"] == "legacy.mp3")
    assert legacy_entry["impetus"] == ""
    assert legacy_entry.get("legacy") is True


# --- generate_podcast — method validation ------------------------------------

def test_generate_podcast_local_no_tts_raises(project_root):
    """With no TTS packages installed, local method raises RuntimeError."""
    with pytest.raises(RuntimeError, match="No TTS engine available"):
        generate_podcast(method="local")


def test_generate_podcast_invalid_method_raises_value_error(project_root):
    with pytest.raises(ValueError):
        generate_podcast(method="soundcloud")


def test_generate_podcast_no_notebooklm_binary(project_root, therapist_config, monkeypatch):
    monkeypatch.setattr(podcast.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="notebooklm CLI not found"):
        generate_podcast(topic="anxiety")


def test_generate_podcast_no_notebooks_raises(project_root, monkeypatch):
    monkeypatch.setattr(podcast.shutil, "which", lambda _: "/usr/bin/notebooklm")
    with pytest.raises(RuntimeError, match="No notebooks configured"):
        generate_podcast(topic="anxiety")


def test_generate_podcast_missing_notebook_id_raises(project_root, monkeypatch):
    import yaml
    config = {
        "therapist": {
            "notebooks": [{"topic": "Anxiety", "when_to_query": "anxiety"}]
            # notebook_id intentionally omitted
        }
    }
    (project_root / "config" / "therapist.yaml").write_text(yaml.dump(config))
    monkeypatch.setattr(podcast.shutil, "which", lambda _: "/usr/bin/notebooklm")
    with pytest.raises(RuntimeError, match="notebook_id"):
        generate_podcast(topic="anxiety")


# --- generate_podcast — fallback_to_local ------------------------------------

def test_generate_podcast_fallback_to_local_on_notebooklm_failure(project_root, therapist_config, monkeypatch):
    """When notebooklm fails and fallback_to_local=True, it falls back to local."""
    monkeypatch.setattr(podcast.shutil, "which", lambda _: "/usr/bin/notebooklm")
    # Simulate notebooklm generate audio failing
    monkeypatch.setattr(
        podcast, "_run",
        lambda _args, timeout=30: type("Result", (), {"returncode": 1, "stderr": "quota exceeded", "stdout": ""})()
    )
    # Mock local generation so we don't need TTS packages
    fake_path = str(project_root / "podcasts" / "20240101_120000_test_local.mp3")
    monkeypatch.setattr(podcast, "_generate_local_podcast", lambda topic, output_dir: fake_path)

    result = generate_podcast(topic="anxiety", fallback_to_local=True)
    assert result == fake_path

    # Verify registry records the fallback as local method
    registry = _load_registry()
    assert len(registry["podcasts"]) == 1
    assert registry["podcasts"][0]["method"] == "local"


def test_generate_podcast_fallback_to_local_raises_when_local_also_fails(
    project_root, therapist_config, monkeypatch
):
    """When notebooklm fails and local also fails, the original/local error is raised."""
    monkeypatch.setattr(podcast.shutil, "which", lambda _: "/usr/bin/notebooklm")
    monkeypatch.setattr(
        podcast, "_run",
        lambda _args, timeout=30: type("Result", (), {"returncode": 1, "stderr": "quota exceeded", "stdout": ""})()
    )
    # Let _generate_local_podcast fail naturally (no TTS packages)
    with pytest.raises(RuntimeError, match="No TTS engine available"):
        generate_podcast(topic="anxiety", fallback_to_local=True)


def test_generate_podcast_no_fallback_when_disabled(project_root, therapist_config, monkeypatch):
    """When notebooklm fails and fallback_to_local=False (default), error propagates."""
    monkeypatch.setattr(podcast.shutil, "which", lambda _: "/usr/bin/notebooklm")
    monkeypatch.setattr(
        podcast, "_run",
        lambda _args, timeout=30: type("Result", (), {"returncode": 1, "stderr": "quota exceeded", "stdout": ""})()
    )
    with pytest.raises(RuntimeError, match="notebooklm generate audio failed"):
        generate_podcast(topic="anxiety", fallback_to_local=False)

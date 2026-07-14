"""Tests for the onboarding wizard UI layer (app/onboarding_wizard.py).

Two levels:
1. Unit tests for the module-level helpers (_match_choice, _merge_update).
2. An end-to-end walk of the wizard through Gradio's queue API against a
   real launched app — this is the harness that would have caught the
   original showstoppers (missing outputs crash on the final confirm,
   consent bypass, stale answer text, unvalidated choice answers).
"""

import json
import shutil
import socket
import urllib.request
from pathlib import Path

import pytest
import yaml

from app.onboarding_wizard import _match_choice, _merge_update

REPO_ROOT = Path(__file__).resolve().parent.parent

CHOICES = ["Direct and challenging", "Gentle and unhurried", "Balanced"]


# ---------------------------------------------------------------------------
# _match_choice
# ---------------------------------------------------------------------------

def test_match_choice_exact():
    assert _match_choice("Balanced", CHOICES) == "Balanced"


def test_match_choice_case_insensitive():
    assert _match_choice("balanced", CHOICES) == "Balanced"


def test_match_choice_unique_substring():
    assert _match_choice("gentle", CHOICES) == "Gentle and unhurried"


def test_match_choice_ambiguous_substring_returns_none():
    # "and" appears in two choices
    assert _match_choice("and", CHOICES) is None


def test_match_choice_no_match_returns_none():
    assert _match_choice("AikoBalancedMixed... nope", ["a", "b"]) is None


def test_match_choice_empty_and_none_return_none():
    assert _match_choice("", CHOICES) is None
    assert _match_choice("   ", CHOICES) is None
    assert _match_choice(None, CHOICES) is None


def test_match_choice_strips_whitespace():
    assert _match_choice("  mixed \n", ["Mixed", "Other"]) == "Mixed"


# ---------------------------------------------------------------------------
# _merge_update
# ---------------------------------------------------------------------------

def test_merge_update_merges_into_existing_dict():
    comp = object()
    updates = {comp: {"__type__": "update", "visible": True, "lines": 4}}
    _merge_update(updates, comp, value="")
    # visibility/lines from the render update must survive the value clear
    assert updates[comp]["visible"] is True
    assert updates[comp]["lines"] == 4
    assert updates[comp]["value"] == ""


def test_merge_update_creates_update_when_absent():
    comp = object()
    updates = {}
    _merge_update(updates, comp, value=[])
    assert updates[comp]["value"] == []
    assert updates[comp]["__type__"] == "update"


def test_merge_update_later_kwargs_win():
    comp = object()
    updates = {comp: {"__type__": "update", "value": "stale"}}
    _merge_update(updates, comp, value="")
    assert updates[comp]["value"] == ""


# ---------------------------------------------------------------------------
# End-to-end wizard walk through the queue API
# ---------------------------------------------------------------------------

class WizardClient:
    """Minimal Gradio queue-API client for driving the wizard."""

    def __init__(self, base_url: str, config: dict, session_hash: str = "pytest"):
        self.base = base_url + "/gradio_api"
        self.session_hash = session_hash
        self.config = config
        self.fn_ids = {
            dep.get("api_name"): dep["id"] for dep in config["dependencies"]
        }
        self.components = {c["id"]: c for c in config["components"]}

    def call(self, api_name: str, data: list) -> dict | None:
        """Join the queue for ``api_name`` and return its completion output.

        Returns a dict mapping "<type>:<label>" (or "<type>:<elem_id>") to
        the update dict for each output component, or None when the event
        errored server-side (Gradio sends {"error": ...} with no data).
        """
        fn_index = self.fn_ids[api_name]
        payload = {
            "data": data,
            "fn_index": fn_index,
            "session_hash": self.session_hash,
        }
        req = urllib.request.Request(
            self.base + "/queue/join",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        json.load(urllib.request.urlopen(req, timeout=15))
        stream = urllib.request.Request(
            self.base + f"/queue/data?session_hash={self.session_hash}"
        )
        with urllib.request.urlopen(stream, timeout=30) as resp:
            for line in resp:
                line = line.decode().strip()
                if not line.startswith("data:"):
                    continue
                msg = json.loads(line[5:])
                if msg.get("msg") == "process_completed":
                    output = msg.get("output", {})
                    if not output.get("data"):
                        return None  # server-side error
                    return self._label_outputs(fn_index, output["data"])
        return None

    def _label_outputs(self, fn_index: int, data: list) -> dict:
        dep = next(d for d in self.config["dependencies"] if d["id"] == fn_index)
        labeled = {}
        for comp_id, value in zip(dep["outputs"], data):
            comp = self.components.get(comp_id, {})
            labeled[f"{comp.get('type')}#{comp_id}"] = value
        return labeled


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def wizard_app(project_root, monkeypatch):
    """Launch the full app (unconfigured → wizard) on a free port."""
    # Real templates are needed by generate_all_config / generate_persona.
    shutil.copytree(REPO_ROOT / "templates", project_root / "templates",
                    dirs_exist_ok=True)
    # Static KB lookups resolve relative to stillpoint/, not project root,
    # so no data/ setup is needed here.

    import app.main as app_main
    monkeypatch.setattr(app_main, "is_configured", lambda: False)

    application = app_main.build_app()
    port = _free_port()
    application.launch(
        server_name="127.0.0.1",
        server_port=port,
        prevent_thread_lock=True,
        quiet=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        cfg = json.load(urllib.request.urlopen(base_url + "/config", timeout=15))
        yield WizardClient(base_url, cfg), cfg, project_root
    finally:
        application.close()


def _initial_component(cfg: dict, ctype: str, **prop_match):
    for comp in cfg["components"]:
        if comp["type"] != ctype:
            continue
        props = comp.get("props", {})
        if all(str(v) in str(props.get(k, "")) for k, v in prop_match.items()):
            return comp
    return None


def test_wizard_full_walkthrough(wizard_app):
    client, cfg, root = wizard_app

    # --- Initial render: first question visible, checkboxes baked in ---
    welcome = _initial_component(cfg, "markdown", value="Welcome to Stillpoint")
    assert welcome is not None, "welcome/disclaimer question must render on load"

    cb = _initial_component(cfg, "checkboxgroup")
    assert cb is not None
    assert len(cb["props"].get("choices", [])) == 14, (
        "multiselect choices must be baked in at build time"
    )

    # --- Next on the info question shows the consent question ---
    out = client.call("on_next", ["", [], None, None, None])
    assert "not a replacement for professional therapy" in str(out)

    # --- Next must NOT advance past (or silently answer) the consent ---
    out = client.call("on_next", ["", [], None, None, None])
    assert "Yes / Confirm" in str(out), "Next on a confirm question must be blocked"

    # --- Confirm advances to the optional name question ---
    out = client.call("on_confirm", [None, None, None])
    assert "What would you like to be called" in str(out)

    # --- Text answers advance; answer box is cleared for the next question ---
    out = client.call("on_next", ["Rich", [], None, None, None])
    assert "design your therapist" in str(out)
    textbox = next(v for k, v in out.items() if k.startswith("textbox#"))
    assert textbox.get("value") == "", "answer text must not leak between questions"

    out = client.call("on_next", ["Aiko", [], None, None, None])
    assert "How direct" in str(out)

    # --- Garbage choice answers are rejected with the valid options ---
    out = client.call("on_next", ["AikoBalanced", [], None, None, None])
    assert "Please choose one of" in str(out)

    # --- Partial matches are canonicalized and advance ---
    out = client.call("on_next", ["balanced", [], None, None, None])
    assert "How structured" in str(out)
    out = client.call("on_next", ["mix", [], None, None, None])
    assert "humor" in str(out)
    out = client.call("on_next", ["occasionally", [], None, None, None])
    assert "specialize in" in str(out)

    # --- Required multiselect rejects an empty submission ---
    out = client.call("on_next", ["", [], None, None, None])
    assert "required" in str(out)

    out = client.call(
        "on_next",
        ["", ["Anxiety & OCD", "ADHD & Executive Function"], None, None, None],
    )
    assert "Describe your ideal therapist" in str(out)

    # --- Optional questions can be skipped ---
    out = client.call("on_skip", [None, None, None])
    assert "LLM Provider" in str(out)

    out = client.call("on_next", ["anthropic", [], None, None, None])
    assert "API key" in str(out)
    out = client.call("on_confirm", [None, None, None])
    assert "Infrastructure Note" in str(out)
    out = client.call("on_next", ["", [], None, None, None])
    assert "Knowledge Base Planning" in str(out)
    out = client.call("on_next", ["", [], None, None, None])
    assert "notebook plan look good" in str(out)

    # --- The final confirm must NOT crash and must reveal the picker ---
    out = client.call("on_confirm", [None, None, None])
    assert out is not None, (
        "final confirm crashed server-side (component missing from outputs?)"
    )
    column_updates = [
        v for k, v in out.items()
        if k.startswith("column#") and isinstance(v, dict)
    ]
    assert any(u.get("visible") is True for u in column_updates), (
        "processing-style picker column must become visible"
    )

    # --- Picker click completes onboarding and writes config files ---
    out = client.call("on_picker_click", [None, None])
    assert out is not None
    assert "Your therapist is ready" in str(out)

    for fname in ("therapist.yaml", "user_profile.yaml", "treatment_plan.yaml"):
        assert (root / "config" / fname).exists(), f"missing {fname}"

    therapist = yaml.safe_load(
        (root / "config" / "therapist.yaml").read_text(encoding="utf-8")
    )
    assert therapist["therapist"]["name"] == "Aiko"
    assert "Anxiety & OCD" in therapist["therapist"]["specializations"]
    assert therapist["llm"]["provider"] == "anthropic"

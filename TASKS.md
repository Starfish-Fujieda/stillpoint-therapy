# Stillpoint — Task List

> **How to use this file**: Read ARCHITECTURE.md first. Then find the first unchecked task below. Implement it. Check the box. Update "Current State" at the top. Commit.
>
> **For AI agents**: After completing a task, update the "Current State" section with what you did, any decisions you made, and what the next agent should pick up.

---

## Current State

**Last completed**: Tasks 1-19 (MVP build — all core functionality)
**Last updated**: 2026-05-16
**Next task**: Task 20 — Report UI, or polish/testing of existing MVP
**Open questions**: None

---

## Task Dependency Graph

```
Tasks 3-5 (foundation) → Tasks 6-8 (templates) → Tasks 9-13 (core library) → Tasks 14-18 (Gradio UI) → Tasks 19-23 (scripts & Docker) → Task 24 (README) → Task 25 (GitHub Actions)
```

---

## Phase 1: Foundation

### Task 1 — Project Scaffold ✅

- [x] Create directory structure
- [x] Create `.gitignore`
- [x] Create `ARCHITECTURE.md`
- [x] Create `TASKS.md`
- [x] `git init` + remote
- **Files**: `.gitignore`, directory structure
- **Done criteria**: All directories exist, `.gitignore` is correct

### Task 2 — Requirements & Package Config ✅

- [x] Create `requirements.txt` with all dependencies
- [x] Create `pyproject.toml` (or `setup.py`) for the `stillpoint` package
- **Dependencies to include**:
  - `gradio>=4.0`
  - `chromadb>=0.4.0`
  - `mempalace>=3.0`
  - `notebooklm` (latest)
  - `pyyaml>=6.0`
  - `jinja2>=3.1`
  - `anthropic>=0.18` (optional)
  - `openai>=1.0` (optional)
  - `google-generativeai` (optional)
- **Files**: `requirements.txt`, `pyproject.toml`
- **Done criteria**: `pip install -e .` works

### Task 3 — Placeholder `__init__.py` Files ✅

- [x] Create `stillpoint/__init__.py` with version and package docstring
- [x] Create `app/__init__.py`
- **Files**: `stillpoint/__init__.py`, `app/__init__.py`
- **Done criteria**: `import stillpoint` works

---

## Phase 2: Templates

### Task 4 — Source Library ✅

- [x] Create `templates/source_library.yaml` with curated books/sources for ~15 clinical topics
- **Files**: `templates/source_library.yaml`
- **Done criteria**: Valid YAML, all topics have at least 3 core sources

### Task 5 — Persona Templates ✅

- [x] Create `templates/therapist_persona.md.tpl` — Jinja2 template for therapist persona markdown
- **Note**: SillyTavern character card JSON removed from scope — persona is generated as system prompt directly
- **Files**: `templates/therapist_persona.md.tpl`
- **Done criteria**: Template renders valid output with test data

### Task 6 — Treatment Plan Template ✅

- [x] Create `templates/treatment_plan.yaml.tpl` — Jinja2 template
- **Files**: `templates/treatment_plan.yaml.tpl`
- **Done criteria**: Template renders valid YAML with test goals

### Task 7 — Referral Resources Template ✅

- [x] Create `templates/referral_resources.md` — Empty template with section headers
- [x] Create `referral_resources.md` at project root — Same empty template
- **Files**: `templates/referral_resources.md`, `referral_resources.md`
- **Done criteria**: Template has all sections with placeholder text

---

## Phase 3: Core Library

### Task 8 — `stillpoint/config.py` — Configuration Loader ✅

- [x] Create config loading/saving utility
- **Files**: `stillpoint/config.py`
- **Done criteria**: Can load/save YAML, detects missing config

### Task 9 — `stillpoint/knowledge.py` — NotebookLM Interface (STUB) ✅

- [x] Implement NotebookLM query wrapper (MVP stub — returns `[UNGROUNDED]` marker)
- **Files**: `stillpoint/knowledge.py`
- **Done criteria**: Returns proper stub response, notebook selection logic works

### Task 10 — `stillpoint/memory.py` — MemPalace Interface (STUB) ✅

- [x] Implement file-based session storage (MVP stub — JSON files, no ChromaDB)
- **Files**: `stillpoint/memory.py`
- **Done criteria**: Can save and retrieve session notes

### Task 11 — `stillpoint/persona.py` — Persona Management ✅

- [x] Implement persona loading and generation
- [x] Generate system prompt from persona markdown (no JSON character card)
- **Files**: `stillpoint/persona.py`
- **Done criteria**: Can generate persona files from onboarding data using templates

### Task 12 — `stillpoint/session.py` — Session Engine ✅

- [x] Implement session lifecycle management
- **Files**: `stillpoint/session.py`
- **Done criteria**: Can process a message through the full pipeline

### Task 13 — `stillpoint/llm.py` — LLM Backend Abstraction ✅

- [x] Implement multi-provider LLM interface (Anthropic, OpenAI, Google, Ollama)
- **Files**: `stillpoint/llm.py`
- **Done criteria**: Can send a message to at least one provider and get a response

---

## Phase 4: Onboarding

### Task 15 — `stillpoint/onboarding.py` — Onboarding Engine ✅

- [x] Implement onboarding interview logic (6 phases)
- [x] Notebook and source recommendation from source library
- **Files**: `stillpoint/onboarding.py`
- **Done criteria**: Can walk through all 6 phases and generate config files

---

## Phase 5: Gradio Web UI

### Task 17 — `app/main.py` — Entry Point ✅

- [x] Create Gradio app entry point with conditional view (onboarding vs chat)
- **Files**: `app/main.py`
- **Done criteria**: `python -m app.main` launches Gradio UI in browser

### Task 18 — `app/onboarding_wizard.py` — Onboarding UI ✅

- [x] Create multi-step onboarding wizard as Gradio interface (6 phases)
- **Files**: `app/onboarding_wizard.py`
- **Done criteria**: Can walk through all 6 phases and generate config

### Task 19 — `app/chat.py` — Chat Interface ✅

- [x] Create therapy chat interface with session lifecycle
- **Files**: `app/chat.py`
- **Done criteria**: Can have a multi-turn conversation with the therapist persona

---

## Post-MVP Tasks (Not Yet Started)

### Task 14 — `stillpoint/report.py` — Report Generation

- [ ] Implement session report generation
- **Files**: `stillpoint/report.py`

### Task 16 — `stillpoint/podcast.py` — Podcast Generation

- [ ] Implement podcast generation (NotebookLM path first)
- **Files**: `stillpoint/podcast.py`

### Task 20 — `app/reports.py` — Report UI

- [ ] Create report generation interface
- **Files**: `app/reports.py`

### Task 21 — `app/settings.py` — Settings UI

- [ ] Create config management interface
- **Files**: `app/settings.py`

### Task 22 — `scripts/setup.sh` ✅

- [x] Create automated setup script
- **Files**: `scripts/setup.sh`
- **Note**: Installs the venv + deps, bootstraps pipx, installs `notebooklm-py[browser]`
  and Chromium, then prompts for the one-time `notebooklm login`. `notebooklm` is an
  external pipx CLI, not a pip dependency — it is not in `requirements.txt`.

### Task 23 — `scripts/save_session.py`

- [ ] Create generalized CLI session saver
- **Files**: `scripts/save_session.py`

### Task 24 — `scripts/generate_report.py`

- [ ] Create CLI report generator
- **Files**: `scripts/generate_report.py`

### Task 25 — `scripts/generate_podcast.py`

- [ ] Create CLI podcast generator
- **Files**: `scripts/generate_podcast.py`

### Task 26 — `scripts/podcast_gap_analyzer.py`

- [ ] Create topic coverage gap analyzer
- **Files**: `scripts/podcast_gap_analyzer.py`

### Task 27 — Dockerfile + docker-compose.yml

- [ ] Create `Dockerfile`
- [ ] Create `docker-compose.yml`
- **Files**: `Dockerfile`, `docker-compose.yml`

### Task 28 — `hipaa_prompt.md`

- [ ] Port from `therapy/hipaa_prompt.md`
- **Files**: `hipaa_prompt.md`

### Task 29 — Onboarding Guides (v2 reference)

- [ ] Create onboarding guide documents
- **Files**: `onboarding/guide_character_design.md`, etc.

### Task 30 — `README.md`

- [ ] Create comprehensive README
- **Files**: `README.md`

### Task 31 — `.github/workflows/validate.yml`

- [ ] Create GitHub Actions workflow
- **Files**: `.github/workflows/validate.yml`

---

## MVP Summary

The MVP includes 16 files across 4 phases:

**Templates** (4 files):
- `templates/source_library.yaml` — 16 clinical topics with 3-5 sources each
- `templates/therapist_persona.md.tpl` — Jinja2 persona template
- `templates/treatment_plan.yaml.tpl` — Jinja2 treatment plan template
- `templates/referral_resources.md` + `referral_resources.md` — Crisis resources template

**Core Library** (6 files):
- `stillpoint/config.py` — YAML config loading/saving
- `stillpoint/knowledge.py` — NotebookLM stub (returns [UNGROUNDED])
- `stillpoint/memory.py` — File-based session storage
- `stillpoint/persona.py` — Persona generation from templates
- `stillpoint/llm.py` — Multi-provider LLM abstraction
- `stillpoint/session.py` — Session lifecycle engine

**Onboarding** (1 file):
- `stillpoint/onboarding.py` — 6-phase onboarding engine

**Gradio UI** (3 files):
- `app/main.py` — Entry point with conditional view
- `app/onboarding_wizard.py` — Multi-step wizard
- `app/chat.py` — Therapy chat interface

---

## Notes for AI Agents

1. **Read ARCHITECTURE.md before starting any task.** It contains settled design decisions.
2. **Check the box and update "Current State" when you finish a task.** The next agent needs to know where things stand.
3. **Commit after each task.** Small, atomic commits with descriptive messages.
4. **If you hit a blocker**, add it to "Open Questions" above and move to the next task you can do.
5. **Don't re-litigate settled decisions.** If ARCHITECTURE.md says something, follow it. If you think it's wrong, note it in "Open Questions" and keep going.
6. **Test your work.** At minimum, verify the file you created is valid (YAML parses, Python imports, template renders).
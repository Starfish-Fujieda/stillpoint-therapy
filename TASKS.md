# Stillpoint — Task List

> **How to use this file**: Read ARCHITECTURE.md first. Then find the first unchecked task below. Implement it. Check the box. Update "Current State" at the top. Commit.
>
> **For AI agents**: After completing a task, update the "Current State" section with what you did, any decisions you made, and what the next agent should pick up.

---

## Current State

**Last completed**: Tasks 27-31 (Dockerfile, docker-compose.yml, hipaa_prompt.md, onboarding guides, README.md, .github/workflows/validate.yml)
**Last updated**: 2026-05-16
**Next task**: Task 14 — `stillpoint/report.py` and Task 16 — `stillpoint/podcast.py` (library implementations needed to make generate_report.py and generate_podcast.py fully functional)
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

- [x] Implement session report generation
- **Files**: `stillpoint/report.py`

### Task 16 — `stillpoint/podcast.py` — Podcast Generation

- [x] Implement podcast generation (NotebookLM path first)
- **Files**: `stillpoint/podcast.py`

### Task 20 — `app/reports.py` — Report UI ✅

- [x] Create report generation interface
- **Files**: `app/reports.py`
- **Note**: Calls `stillpoint.report.generate_session_report()` via lazy import; shows a clear
  "not yet available" message until Task 14 is merged. Includes date range, section toggles,
  anonymize toggle, and Markdown download.

### Task 21 — `app/settings.py` — Settings UI ✅

- [x] Create config management interface
- **Files**: `app/settings.py`
- **Note**: Edits LLM backend, notebooks (via Dataframe), therapist preferences, and referral
  resources. Validates notebook topics before saving. Both tabs wired into `app/main.py` via
  `gr.Tabs()`.

### Task 22 — `scripts/setup.sh` ✅

- [x] Create automated setup script
- **Files**: `scripts/setup.sh`
- **Note**: Installs the venv + deps, bootstraps pipx, installs `notebooklm-py[browser]`
  and Chromium, then prompts for the one-time `notebooklm login`. `notebooklm` is an
  external pipx CLI, not a pip dependency — it is not in `requirements.txt`.

### Task 23 — `scripts/save_session.py` ✅

- [x] Create generalized CLI session saver
- **Files**: `scripts/save_session.py`
- **Note**: Reads from `config/sessions/` JSON store. Supports `--list`, `--session-id`, `--output`. Default export to `exports/session_YYYY-MM-DD.md`.

### Task 24 — `scripts/generate_report.py` ✅

- [x] Create CLI report generator
- **Files**: `scripts/generate_report.py`
- **Note**: Calls `stillpoint.report.generate_session_report()`. Handles `ImportError` gracefully with a clear message. Supports `--since`, `--sections`, `--anonymize`, `--output`.

### Task 25 — `scripts/generate_podcast.py` ✅

- [x] Create CLI podcast generator
- **Files**: `scripts/generate_podcast.py`
- **Note**: Calls `stillpoint.podcast.generate_podcast()`. Handles `ImportError` gracefully. Supports `--topic`, `--method` (notebooklm|local), `--output-dir`.

### Task 26 — `scripts/podcast_gap_analyzer.py` ✅

- [x] Create topic coverage gap analyzer
- **Files**: `scripts/podcast_gap_analyzer.py`
- **Note**: Reads `templates/source_library.yaml` and scans `podcasts/` dir. Ranks uncovered topics by priority (required topics first, then by treatment goal relevance). Supports `--suggest` for next-topic recommendation.

### Task 27 — Dockerfile + docker-compose.yml ✅

- [x] Create `Dockerfile`
- [x] Create `docker-compose.yml`
- **Files**: `Dockerfile`, `docker-compose.yml`
- **Note**: NotebookLM CLI cannot be containerized (browser auth required). Documented in Dockerfile comments. All other features work. Named volume `palace_data` persists ChromaDB across container restarts.

### Task 28 — `hipaa_prompt.md` ✅

- [x] Create `hipaa_prompt.md`
- **Files**: `hipaa_prompt.md`
- **Note**: Covers all 18 HIPAA PHI categories, includes a copyable scanning prompt, redaction guidance, and a table of what Stillpoint stores locally.

### Task 29 — Onboarding Guides (v2 reference) ✅

- [x] Create onboarding guide documents
- **Files**: `onboarding/guide_character_design.md`, `onboarding/guide_notebook_planning.md`, `onboarding/guide_source_selection.md`
- **Note**: Three guides created. `guide_source_selection.md` covers all 14 tailored notebook topics with sourced book recommendations.

### Task 30 — `README.md` ✅

- [x] Create comprehensive README
- **Files**: `README.md`
- **Note**: Covers quickstart, features, config, Docker limitation, privacy model, limitations (honest about MVP state), crisis resources, and acknowledgments.

### Task 31 — `.github/workflows/validate.yml` ✅

- [x] Create GitHub Actions workflow
- **Files**: `.github/workflows/validate.yml`
- **Note**: No `tests/` directory exists so CI runs import checks + py_compile across all .py files. Checks both `stillpoint.*` and `app.*` modules individually.

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
# Stillpoint

An AI-assisted self-therapy framework. Stillpoint gives you a customizable
therapist persona grounded in actual clinical literature, persistent memory
across sessions, and structured reports you can share with a human therapist.

---

## What Is Stillpoint?

Stillpoint provides:

- **A customizable therapist persona** designed during onboarding to match
  your preferences and the clinical areas you want to work on
- **Clinical knowledge grounding** via Google NotebookLM — responses are
  anchored in real books you load, not improvised from training data
- **Persistent session memory** — the system remembers what you've discussed
  and builds on it across sessions
- **Session reports** — structured summaries you can download and share with
  a human therapist
- **Podcast generation** — audio recaps from your session content via
  NotebookLM's Audio Overview feature

### What Stillpoint Is NOT

Stillpoint is a self-work tool. It is not:

- A substitute for professional therapy
- A diagnostic tool
- A crisis intervention service
- A medical device

If you are in crisis right now, please stop and contact a crisis resource.
See the [Crisis Resources](#crisis-resources) section below.

---

## What You'll Need

- **Python 3.11 or later** (3.12+ works)
- **A Google account** with access to [NotebookLM](https://notebooklm.google.com)
  (free tier is sufficient)
- **An LLM API key** for at least one provider:
  - [Anthropic](https://console.anthropic.com/) (Claude — recommended)
  - [OpenAI](https://platform.openai.com/)
  - [Google AI](https://aistudio.google.com/)
  - Ollama (local, no API key needed)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/stillpoint-therapy.git
cd stillpoint-therapy

# Run setup (creates a virtualenv, installs deps, sets up the NotebookLM CLI)
bash scripts/setup.sh

# Authenticate NotebookLM (one-time, opens browser)
notebooklm login

# Set your LLM API key (or add to your shell profile)
export ANTHROPIC_API_KEY="your-key-here"

# Activate the virtualenv and launch
source .venv/bin/activate
python -m app.main
```

Then open [http://localhost:7860](http://localhost:7860) in your browser.

On first launch, Stillpoint detects that no configuration exists and opens
the onboarding wizard. This takes 15-30 minutes to complete.

---

## Features

### Therapist Persona

During onboarding, you design your therapist: name, communication style,
cultural context, specializations, and therapeutic approach. The result is
a persona file that becomes the system prompt for all sessions.

The default therapeutic framework is **ACT + IFS** (Acceptance and Commitment
Therapy + Internal Family Systems). You can request alternatives (CBT, DBT,
psychodynamic) during onboarding.

See [onboarding/guide_character_design.md](onboarding/guide_character_design.md)
for a detailed guide.

### Session Memory

Stillpoint remembers what you've discussed. At the start of each session,
it loads relevant context from past sessions — not everything, just what's
most relevant to what you're currently working on.

Memory is stored locally in `~/.stillpoint/palace/`. Nothing is sent to
any cloud service.

### Clinical Knowledge Base (NotebookLM)

Before giving clinical guidance, the session engine queries your NotebookLM
notebooks — organized by topic — to ground the response in actual source
material. If the notebooks don't contain a relevant source, the response is
labeled `[UNGROUNDED]` rather than improvised.

You create the notebooks in NotebookLM and add the books you've chosen.
The onboarding wizard recommends which notebooks to create and which sources
to add. See [onboarding/guide_notebook_planning.md](onboarding/guide_notebook_planning.md)
and [onboarding/guide_source_selection.md](onboarding/guide_source_selection.md).

### Session Reports

After a session or series of sessions, Stillpoint can generate a structured
report covering:

- Themes worked on
- Goal progress
- New disclosures
- Coping strategies attempted
- Emotional trajectory
- Red flags (if any)
- Patterns observed
- Homework and practices

Reports are generated locally and downloaded as Markdown. You control what
to include and whether to share them.

Before sharing a report with a human therapist, run the PHI scan:
see [hipaa_prompt.md](hipaa_prompt.md).

### Podcast Generation

NotebookLM's Audio Overview feature can generate audio summaries from session
content or specific topics. This is useful for processing key themes between
sessions. Launch it from the Gradio UI's "Generate Podcast" button.

---

## Configuration

All configuration lives in `config/` (gitignored — your data stays local).

| File | What it controls |
|------|-----------------|
| `config/therapist.yaml` | Persona name, specializations, LLM provider, notebook IDs |
| `config/user_profile.yaml` | Processing style, adaptations |
| `config/treatment_plan.yaml` | Session goals, exit-ramp state, session log |
| `config/podcast.yaml` | Podcast preferences |

To change your LLM provider:

```yaml
# config/therapist.yaml
llm:
  provider: openai          # anthropic | openai | google | ollama
  model: gpt-4o
  api_key_env: OPENAI_API_KEY
```

To add a new notebook after onboarding:

```yaml
# config/therapist.yaml
therapist:
  notebooks:
    - topic: "Grief & Loss"
      notebook_id: "abc123def456"
      when_to_query: "grief, loss, bereavement, mourning"
```

---

## Docker

Docker is available for users who prefer containerized environments.

```bash
docker compose up
```

Open [http://localhost:7860](http://localhost:7860).

**Important limitation**: NotebookLM grounding is not available inside the
container (browser authentication cannot be automated). All other features
work normally. For full functionality, run natively using `scripts/setup.sh`.

Environment variables (pass via shell or `.env` file):

```bash
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
GOOGLE_API_KEY=your-key
```

---

## Privacy

Stillpoint is designed for local use. Here is exactly what goes where:

| Data | Where it lives | Who can access it |
|------|---------------|-------------------|
| Session notes | `~/.stillpoint/palace/` (local) | You only |
| Config and personas | `config/`, `personas/` (local, gitignored) | You only |
| Generated reports | Wherever you save them | You control |
| In-session messages | Sent to your LLM provider (Anthropic, OpenAI, etc.) | Your provider's privacy policy applies |

Stillpoint does not send telemetry, usage data, or session content to any
server under its control.

Before sharing session reports with a human therapist, scan for PHI using
the prompt in [hipaa_prompt.md](hipaa_prompt.md).

---

## Limitations

Stillpoint is experimental software. Know these before you start:

- **NotebookLM is required for grounded responses.** Without it, the session
  engine uses the LLM's training data, which is broader and less reliable.
  Responses will be labeled `[UNGROUNDED]`.

- **Session memory is file-based in the current MVP.** ChromaDB vector search
  is configured but the MVP uses JSON file storage. This means semantic search
  across sessions is limited until ChromaDB is fully integrated.

- **The onboarding wizard generates config but cannot populate notebooks.**
  You create the NotebookLM notebooks and add sources manually. The wizard
  tells you exactly what to create and why.

- **Report and podcast generation are stub implementations in the current MVP.**
  The UI exists; the underlying generation logic is in progress.

- **No multi-user support.** This is a single-user local tool.

---

## Crisis Resources

If you are in immediate danger or experiencing a mental health emergency,
contact emergency services or a crisis line now.

**United States**
- 988 Suicide & Crisis Lifeline: Call or text **988**
- Crisis Text Line: Text HOME to **741741**
- National Domestic Violence Hotline: 1-800-799-7233

**International**
- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/
- Crisis Lines International: https://www.crisislines.com/

**If you are outside the US**, contact your local emergency services (equivalent
to 911) or search "[your country] mental health crisis line."

Stillpoint will not fabricate crisis resources. Your `referral_resources.md`
file is the place to add verified local resources specific to your area.

---

## License

MIT License. See `LICENSE` for full text.

The default therapeutic framework (ACT + IFS) is based on the published work
of Steven Hayes, Russ Harris, Richard Schwartz, and others. Their work is cited
in the source library. Stillpoint does not reproduce copyrighted text.

---

## Acknowledgments

Stillpoint's clinical framework draws on:

- Acceptance and Commitment Therapy (Hayes, Strosahl, Wilson)
- Internal Family Systems (Richard Schwartz)
- Self-Compassion research (Kristin Neff)
- Shame resilience work (Brené Brown)
- Trauma-informed approaches (Bessel van der Kolk, Pete Walker)

The name Stillpoint comes from T.S. Eliot's *Four Quartets*:
"At the still point of the turning world... there the dance is."

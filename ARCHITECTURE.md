# Stillpoint — Architecture Document

> **Status**: v1 Design
> **Last Updated**: 2026-05-16
> **Decisions here are settled.** If you want to change something, discuss with the project owner first and update this document.

---

## What Is Stillpoint?

Stillpoint is an AI-assisted self-therapy framework. It provides:

1. **A customizable therapist persona** — designed during onboarding to match the user's preferences and clinical needs
2. **A clinical knowledge base** — powered by Google NotebookLM, organized into topic-specific notebooks
3. **Persistent session memory** — using MemPalace (ChromaDB-backed vector store) for cross-session continuity
4. **A web-based chat interface** — Gradio UI for accessible, browser-based therapy sessions
5. **Session reports** — structured summaries for sharing with a human therapist
6. **Podcast generation** — audio recaps from session content (via NotebookLM or local TTS)

### What Stillpoint Is NOT

- A substitute for professional therapy
- A diagnostic tool
- A crisis intervention service
- A medical device

---

## Design Principles

1. **Shame is incompatible with change.** Everything about the system — the persona, the language, the flow — must reinforce non-judgmental curiosity.
2. **The system's success is its own reduced use.** Built-in exit-ramp and step-down protocols encourage users to eventually need it less.
3. **Clinical grounding before advice.** Every therapeutic response is grounded in NotebookLM knowledge, never fabricated from training data alone.
4. **User ownership of data.** All data stays local (ChromaDB on the user's machine). No telemetry. No cloud storage of sessions.
5. **Accessibility first.** The Gradio UI is the primary interface. AI harness integration (Claude Code, Kilo) is an advanced option for power users.

---

## Target Users

| User Type             | Use Case                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------------- |
| Self-therapy seeker   | Uses the web UI for guided self-work between human therapy sessions or as standalone support |
| Therapy supplementer  | Generates structured session reports to share with their human therapist                     |
| Therapist / counselor | Generates psychoeducational podcasts for clients; may use the persona as a sounding board    |
| Developer / tinkerer  | Uses the AI harness path (Claude Code, Kilo) for full control and customization              |

---

## Technology Stack

| Component               | Technology                                           | Why                                                                     |
| ----------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------- |
| Web UI                  | Gradio                                               | Accessible, Python-native, easy to containerize, no frontend build step |
| Clinical Knowledge      | Google NotebookLM                                    | Topic-partitioned notebooks with source-grounded Q&A                    |
| Session Memory          | MemPalace + ChromaDB                                 | Local vector store, semantic search across sessions                     |
| LLM Backend             | User's choice (Anthropic / OpenAI / Google / Ollama) | Configurable via `config/therapist.yaml`                                |
| Language                | Python 3.11+                                         | Required by MemPalace and ChromaDB                                      |
| Containerization        | Docker + Docker Compose                              | Optional: isolates dependencies, simplifies setup                       |
| Podcast (easy path)     | NotebookLM Audio Overview                            | Built-in, no local TTS needed                                           |
| Podcast (advanced path) | Podcastfy + local TTS (e.g., Alexandria/Qwen3-TTS)   | Unlimited generation, no API quotas                                     |

---

## File Structure

```
stillpoint-therapy/
├── ARCHITECTURE.md              # THIS FILE — stable design decisions
├── TASKS.md                     # Ordered task list with checkboxes
├── README.md                    # User-facing docs + quickstart guide
├── .gitignore
│
├── stillpoint/                  # Core Python library
│   ├── __init__.py
│   ├── knowledge.py             # NotebookLM query wrapper
│   ├── memory.py                # MemPalace read/write wrapper
│   ├── session.py               # Session protocol engine
│   ├── persona.py               # Persona loading & generation
│   ├── report.py                # Report generation for human therapists
│   ├── podcast.py               # Podcast generation (NotebookLM + local)
│   └── onboarding.py            # Onboarding interview logic
│
├── app/                         # Gradio web UI
│   ├── main.py                  # Entry point: `python -m app.main`
│   ├── chat.py                  # Chat interface (therapy sessions)
│   ├── onboarding_wizard.py     # Step-by-step onboarding UI
│   ├── reports.py               # Report generation & download UI
│   └── settings.py              # Config management UI
│
├── config/                      # Generated config (gitignored)
│   ├── therapist.yaml           # Character config, notebook IDs, specializations
│   ├── treatment_plan.yaml      # Goals, session log, exit-ramp state
│   ├── user_profile.yaml        # Processing style, preferences, adaptations
│   └── podcast.yaml             # Podcast preferences (NotebookLM vs local)
│
├── personas/                    # Generated personas (gitignored)
│   ├── therapist.md             # Full clinical profile (from onboarding)
│   └── therapist.json           # Character card (from onboarding)
│
├── templates/                   # Templates used during onboarding
│   ├── therapist_persona.md.tpl # Jinja2 template for persona markdown
│   ├── therapist_card.json.tpl  # Jinja2 template for character card JSON
│   ├── treatment_plan.yaml.tpl  # Jinja2 template for treatment plan
│   ├── referral_resources.md    # Empty template for user's local resources
│   └── source_library.yaml      # Curated books/sources by clinical topic
│
├── onboarding/                  # Onboarding resources (AI harness path, v2)
│   ├── guide_character_design.md
│   ├── guide_notebook_planning.md
│   ├── guide_processing_style.md
│   └── skills/                  # Cline/Claude Code skills for AI harness onboarding
│       ├── 01_welcome.md
│       ├── 02_character_designer.md
│       ├── 03_infrastructure.md
│       ├── 04_notebook_advisor.md
│       ├── 05_source_recommender.md
│       └── 06_processing_style.md
│
├── scripts/                     # CLI utilities
│   ├── setup.sh                 # Automated infrastructure setup
│   ├── save_session.py          # Save session to both ChromaDB collections
│   ├── generate_report.py       # Generate session report for human therapist
│   ├── generate_podcast.py      # Podcast generation (both paths)
│   └── podcast_gap_analyzer.py  # Analyze topic coverage gaps
│
├── Dockerfile                   # Container build
├── docker-compose.yml           # Container orchestration
│
├── hipaa_prompt.md              # PHI scanning prompt (reuse from therapy project)
└── referral_resources.md        # User-maintained crisis/referral resources
```

---

## Configuration Architecture

### `config/therapist.yaml` (Generated)

```yaml
# Generated during onboarding — DO NOT EDIT MANUALLY unless you know what you're doing
therapist:
  name: "Dr. Sarah Chen"                    # Chosen by user
  description: "..."                         # From character design
  specializations: [anxiety, grief, ...]     # From clinical landscape interview
  
  # NotebookLM notebooks (IDs filled in during infrastructure setup)
  notebooks:
    - topic: "Core Therapy Techniques"
      notebook_id: ""                        # User fills in after creating in NotebookLM
      when_to_query: "Therapeutic technique, ACT, IFS, CBT"
    - topic: "Self-Compassion & Shame Resilience"
      notebook_id: ""
      when_to_query: "Self-compassion, shame, emotional regulation"
    # ... additional notebooks based on user's clinical landscape

# LLM Backend
llm:
  provider: anthropic          # anthropic | openai | google | ollama
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY   # Name of env var (not the key itself)
  # For local:
  # provider: ollama
  # model: llama3
  # base_url: http://localhost:11434

# MemPalace
memory:
  palace_path: ~/.stillpoint/palace
  collections:
    - mempalace_drawers
    - therapy
  wing: therapy
  agent_name: therapist                   # Derived from therapist name

# Session protocol
session:
  exit_ramp_cadence: 5                    # Ask meta-question every N sessions
  session_unit: therapy-day               # session_n counts days, not contacts
```

### `config/user_profile.yaml` (Generated)

```yaml
# User preferences and processing style (from onboarding)
user:
  name: ""                                 # Optional
  
processing_style:
  alexithymia_adapted: false               # If true: cognitive framing, no somatic questions
  intellectualizing_redirects: true         # If true: redirect after 3+ analytical exchanges
  sensory_considerations: false
  communication_preference: ""              # direct | gentle | mixed
  
# Custom adaptations detected during sessions (updated dynamically)
adaptations: []
```

### `config/treatment_plan.yaml` (Generated)

```yaml
metadata:
  created: ""
  last_updated: ""
  version: 1

intake_goals: []         # Populated from onboarding interview

step_down_milestone:
  description: "..."
  criteria: []
  transition_options: []
  session_count_at_last_update: 0

exit_ramp:
  session_unit: therapy-day
  total_contacts: 0
  meta_question_cadence: 5
  last_meta_question_session: null

session_log: []
```

---

## Core Library (`stillpoint/`)

### `stillpoint/knowledge.py` — NotebookLM Interface

```python
def query_knowledge(question: str, topics: list[str] | None = None) -> str:
    """Query the appropriate NotebookLM notebook(s) for clinical grounding.
    
    - If topics provided, query only those notebooks
    - If no topics, analyze the question and select relevant notebooks
    - Retry on timeout (up to 3 attempts)
    - Return grounded response or label as [UNGROUNDED]
    """
```

### `stillpoint/memory.py` — MemPalace Interface

```python
def save_session_notes(content: str) -> bool:
    """Save session notes to both ChromaDB collections."""

def search_sessions(query: str, results: int = 20) -> list[str]:
    """Semantic search across past sessions."""

def get_wake_up_context() -> str:
    """Get condensed L0+L1 context for session start."""

def get_session_count() -> int:
    """Return total number of stored sessions."""
```

### `stillpoint/session.py` — Session Engine

```python
class SessionEngine:
    """Manages the therapy session lifecycle."""
    
    def start_session(self) -> dict:
        """Run session start protocol: check date, load memory, load treatment plan."""
    
    def process_message(self, user_message: str) -> str:
        """Process a user message through the full pipeline:
        1. Load persona as system prompt
        2. Query MemPalace for relevant past context
        3. Query NotebookLM for clinical grounding
        4. Send to LLM backend
        5. Return response
        """
    
    def end_session(self, session_notes: str) -> bool:
        """Run session end protocol:
        1. Save notes to MemPalace
        2. Update treatment_plan.yaml
        3. Return success/failure
        """
```

### `stillpoint/persona.py` — Persona Management

```python
def load_persona() -> dict:
    """Load the therapist persona from config/ and personas/."""

def generate_persona(onboarding_data: dict) -> None:
    """Generate persona files from onboarding interview data using templates."""

def validate_persona() -> list[str]:
    """Check that all required persona fields are present. Return list of issues."""
```

### `stillpoint/report.py` — Report Generation

```python
def generate_session_report(sessions: list[str] | None = None) -> str:
    """Generate a structured markdown report from session data.
    
    If sessions is None, report on all sessions since last report.
    
    Report sections:
    1. Themes Covered
    2. Goal Progress
    3. New Disclosures
    4. Coping Strategies Attempted
    5. Emotional Trajectory
    6. Red Flags (if any)
    7. Patterns Observed
    8. Homework/Practices Assigned
    9. Client's Own Words (anonymizable)
    """
```

### `stillpoint/podcast.py` — Podcast Generation

```python
def generate_podcast(topic: str | None = None, method: str = "notebooklm") -> str:
    """Generate a therapy podcast episode.
    
    method: "notebooklm" (Audio Overview) or "local" (Podcastfy + TTS)
    topic: If provided, generate about this topic. If None, auto-select uncovered topic.
    
    Returns path to generated audio file.
    """
```

### `stillpoint/onboarding.py` — Onboarding Logic

```python
class OnboardingEngine:
    """Manages the onboarding interview process."""
    
    PHASES = ["welcome", "character_design", "infrastructure", "notebooks", "sources", "processing_style"]
    
    def get_next_question(self, phase: str, answers: dict) -> str:
        """Return the next interview question for the current phase."""
    
    def process_answer(self, phase: str, answer: str) -> dict:
        """Process the user's answer and return updated state."""
    
    def generate_config(self, all_answers: dict) -> None:
        """Generate all config files from completed onboarding."""
    
    def recommend_notebooks(self, clinical_landscape: dict) -> list[dict]:
        """Analyze clinical landscape and propose notebook topology."""
    
    def recommend_sources(self, notebooks: list[dict]) -> list[dict]:
        """Recommend books/sources for each notebook from the source library."""
```

---

## Gradio Web UI (`app/`)

### `app/main.py` — Entry Point

```
Open browser → http://localhost:7860

If no config exists → redirect to onboarding wizard
If config exists → show chat interface
```

### `app/chat.py` — Chat Interface

- Displays therapist chat with message history
- "End Session" button triggers session end protocol
- "Generate Report" button opens report UI
- "Generate Podcast" button opens podcast UI
- Status indicator: session count, last session date, treatment goal progress

### `app/onboarding_wizard.py` — Onboarding UI

Multi-step wizard with 6 phases:

1. **Welcome** — What is Stillpoint, what to expect, consent
2. **Character Design** — Interview about therapist preferences (gender, age, style, specializations)
3. **Infrastructure Setup** — Guided setup of NotebookLM + MemPalace (with `setup.sh` integration)
4. **Notebook Planning** — Interview about clinical concerns → proposed notebook topology
5. **Source Recommendations** — For each notebook, suggest books/sources with explanations
6. **Processing Style** — Optional: adapt the persona to the user's processing style

### `app/reports.py` — Report UI

- Select date range or "since last report"
- Choose which sections to include
- Generate and download as Markdown or PDF

### `app/settings.py` — Config Management

- Edit LLM backend settings
- Add/remove notebooks
- Update therapist preferences
- Manage referral resources

---

## Onboarding Guide: Character Design

### Research-Based Therapist Matching Factors

The onboarding wizard guides users through these evidence-based factors for choosing a therapist:

1. **Therapeutic Alliance** — The #1 predictor of therapy outcomes (not modality, not experience). The user needs to feel safe, understood, and not judged. The character should be designed so the user *wants* to talk to them.

2. **Identity Matching** — Research shows clients often benefit from therapists who share or deeply understand their cultural, gender, or life-experience background. Options:
   - Gender preference (same gender, different gender, no preference)
   - Cultural background (shared culture, cross-cultural, no preference)
   - Age proximity (similar age, older mentor figure, no preference)
   - Life experience overlap (expat, recovery, parenthood, LGBTQ+, etc.)

3. **Communication Style** — How the therapist talks:
   - Direct/challenging vs. gentle/unhurried
   - Structured (agenda-driven) vs. organic (follows the client's lead)
   - Uses humor or doesn't
   - Asks questions vs. offers interpretations
   - Formal vs. casual

4. **Specialization Alignment** — The therapist should have experience with the user's specific concerns. The wizard maps concerns to specializations.

5. **Therapeutic Approach** — Default is ACT + IFS (the framework's foundation). Users can request alternatives (CBT, DBT, psychodynamic, etc.) which affects the source library recommendations.

### Default Character: Eli (Onboarding Guide)

During onboarding, the guide character is **Eli** — warm, curious, clinically expert, with no specific geographic location. He's defined by his therapeutic presence, not where he lives. He helps the user design *their* therapist. After onboarding, Eli steps back and the user's custom therapist takes over.

---

## Onboarding Guide: Notebook Planning

### Minimum Required Notebooks

Based on clinical best practice, every user gets these two notebooks:

1. **Core Therapy Techniques** — ACT/IFS foundations, therapeutic technique, mindfulness
   - Everyone needs a framework for understanding their own process
   - Sources: Russ Harris (ACT), Richard Schwartz (IFS), general CBT/mindfulness texts

2. **Self-Compassion & Shame Resilience** — Shame is the universal enemy of change
   - Regardless of presenting concern, shame will be a factor
   - Sources: Kristin Neff, Brené Brown (shame resilience), Christopher Germer

### Tailored Notebooks

After the minimum two, the wizard proposes additional notebooks based on the clinical landscape interview:

- CPTSD & Trauma
- ADHD & Executive Function
- ASD & Neurodivergence
- Anxiety & OCD
- Depression & Mood
- Substance Use & Recovery
- Compulsive Sexual Behavior
- Grief & Loss
- Relationship & Attachment
- Anger & Emotional Regulation
- Body Image & Eating Concerns
- Digital Addiction
- Sleep & Chronic Health
- Identity & Life Transitions

Each topic has 3-5 core sources and 2-3 supplemental sources in `templates/source_library.yaml`.

### Notebook Size Guidelines

- **3-5 sources per notebook** is the sweet spot for NotebookLM
- Too few sources → shallow responses
- Too many sources → diluted responses, slower queries
- Each source should be a complete book or substantial document (not just articles)

---

## Onboarding Guide: Processing Style

### What We Assess (Optional)

The wizard offers to ask about processing style. This is optional — the user can skip it and let the therapist detect patterns during sessions.

**Factors:**

1. **Alexithymia** — Difficulty identifying emotions in real time
   - Adaptation: cognitive/experiential framing, no somatic questions
   - Ask: "When someone asks 'how are you feeling?', is your answer usually cognitive ('I'm thinking about...') or emotional ('I feel...')?"

2. **Intellectualizing tendency** — Processing through analysis rather than experience
   - Adaptation: redirect after 3+ analytical exchanges without new disclosure
   - Note: For neurodivergent users, intellectualizing may be genuine processing, not avoidance

3. **Sensory sensitivities** — Environmental factors that affect regulation
   - Adaptation: acknowledge sensory considerations in session framing

4. **Communication preference** — Directness vs. gentleness
   - Direct: "Here's what I notice..." / Gentle: "I'm wondering if..."

5. **Social demand tolerance** — How much interpersonal pressure the user can handle
   - Adaptation: adjust how assertively the therapist pushes

### Dynamic Adaptation

The system also detects patterns during sessions and adds adaptations to `config/user_profile.yaml`:

- If the user consistently responds to "how do you feel?" with thoughts → flag alexithymia adaptation
- If the user intellectualizes for 3+ exchanges → flag redirect adaptation
- If the user avoids specific topics → note avoidance pattern

---

## Session Protocol

### Session Start
1. Check date/time
2. Load MemPalace wake-up context
3. Load treatment plan
4. Query NotebookLM if clinical grounding needed
5. Open with: "How are you arriving? What's the headline right now?"

### During Session
- Follow the therapist persona: warm, boundaried, curious, non-pathologizing
- Use IFS parts language when discussing compulsive behavior
- Meet the user in their processing style (cognitive, emotional, mixed)
- Query NotebookLM before giving clinical advice
- Hold the distinction between intrusive thoughts and intent
- Never moralize, rush, or collapse distinctions

### Session End
1. Summarize key themes
2. Note patterns or breakthroughs
3. Save session notes to MemPalace (both collections)
4. Update `treatment_plan.yaml`
5. Check exit-ramp criteria

### Exit-Ramp Protocol
- Every 5 sessions: ask "How is this arrangement fitting into your life?"
- When step-down criteria are partially met: discuss transition
- Success metric: the user needs the system less over time

---

## Session Reports for Human Therapists

### What a Human Therapist Would Want to Know

A structured report includes:

1. **Themes Covered** — What the client worked on (not raw transcripts)
2. **Goal Progress** — Movement on stated treatment goals
3. **New Disclosures** — Anything raised for the first time
4. **Coping Strategies Attempted** — What was tried, what worked/didn't
5. **Emotional Trajectory** — Trends across sessions (improving, stable, declining)
6. **Red Flags** — Any crisis language, escalation, new risky behaviors
7. **Patterns Observed** — Recurring themes, avoidance patterns, breakthroughs
8. **Homework/Practices Assigned** — Between-session work suggested
9. **Client's Own Assessment** — What they found helpful/unhelpful

### Privacy Controls

- User chooses what to include/exclude before sharing
- Names and identifiers can be anonymized
- Report is generated locally, never transmitted automatically

---

## Boundaries & Safety

### What the System NEVER Does

- Prescribe medication or diagnose
- Generate or improvise therapist names, clinic addresses, or phone numbers
- Moralize, express disgust, or treat behavior as character flaws
- Confuse the AI role with friendship
- Tell the user what to feel
- Recommend willpower-based approaches for executive dysfunction

### Crisis Protocol

If the user expresses active suicidal intent with a plan:
- The system responds with compassion, not panic
- Recommends professional emergency resources (from `referral_resources.md` only)
- If no resources are listed for the user's location: "I don't have a verified resource for your area. Please contact your local emergency services or crisis line."
- Never fabricates referral information

### HIPAA Compliance

The `hipaa_prompt.md` file provides a prompt for scanning project data for PHI violations. Users who share reports with human therapists should run this scan first.

---

## Docker Architecture

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Install stillpoint package
RUN pip install -e .

# Expose Gradio port
EXPOSE 7860

# Default: launch Gradio UI
CMD ["python", "-m", "app.main"]
```

### docker-compose.yml

```yaml
services:
  stillpoint:
    build: .
    ports:
      - "7860:7860"
    volumes:
      - ./config:/app/config           # Generated config files
      - ./personas:/app/personas       # Generated personas
      - ./templates:/app/templates     # Templates (read-only)
      - palace_data:/root/.stillpoint/palace  # Persistent memory
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      # Or: - OPENAI_API_KEY=${OPENAI_API_KEY}
      # Or: - GOOGLE_API_KEY=${GOOGLE_API_KEY}

volumes:
  palace_data:
```

---

## Conventions

### Code Style
- Python 3.11+, type hints encouraged
- 4-space indentation, max line length 100
- Functions have docstrings
- Error handling: catch specific exceptions, never bare `except`

### File Naming
- Python modules: `snake_case.py`
- Templates: `snake_case.ext.tpl` (Jinja2 templates)
- Config: `snake_case.yaml`
- Markdown: `snake_case.md`

### Configuration
- All user-specific config goes in `config/` (gitignored)
- Templates in `templates/` are committed (not gitignored)
- Environment variables for secrets (API keys), never hardcoded
- Config files use YAML (not JSON) for readability and comments

### Dependencies
- `requirements.txt` at project root
- Core dependencies: `gradio`, `chromadb`, `mempalace`, `notebooklm`, `pyyaml`, `jinja2`
- Optional: `podcastfy`, `anthropic`, `openai`, `google-generativeai`

---

## Source Library Format

`templates/source_library.yaml` contains the curated book/source recommendations:

```yaml
topics:
  core_therapy_techniques:
    display_name: "Core Therapy Techniques"
    description: "Foundational therapeutic frameworks — ACT, IFS, CBT, mindfulness"
    required: true                    # Every user gets this notebook
    core_sources:
      - title: "The Happiness Trap"
        author: "Russ Harris"
        type: book
        why: "Accessible ACT introduction for clients and practitioners"
      - title: "No Bad Parts"
        author: "Richard Schwartz"
        type: book
        why: "IFS fundamentals written for a general audience"
    supplemental_sources:
      - title: "Get Out of Your Mind and Into Your Life"
        author: "Steven Hayes"
        type: book
        why: "ACT workbook with practical exercises"

  self_compassion_shame:
    display_name: "Self-Compassion & Shame Resilience"
    description: "Shame resilience, self-compassion, emotional regulation"
    required: true
    core_sources:
      - title: "Self-Compassion: The Proven Power of Being Kind to Yourself"
        author: "Kristin Neff"
        type: book
        why: "Foundational self-compassion research and practice"
      - title: "I Thought It Was Just Me (But It Isn't)"
        author: "Brené Brown"
        type: book
        why: "Shame resilience framework — accessible, research-grounded"
    supplemental_sources:
      - title: "The Mindful Path to Self-Compassion"
        author: "Christopher Germer"
        type: book

  # ... 13-18 more topics
```

---

## Phases of Development

### v1 — Core Product
- Core Python library (`stillpoint/`)
- Gradio web UI with onboarding wizard
- Docker containerization
- `setup.sh` for native installation
- NotebookLM integration
- MemPalace integration
- Session protocol engine
- Report generation
- Podcast generation (NotebookLM path)
- README + quickstart guide

### v2 — Advanced Features
- AI harness integration (CLAUDE.md, Kilo skills, SillyTavern support)
- Podcast generation (local TTS path)
- Dynamic processing style detection
- Treatment plan visualization in UI
- Multi-language support
- Podcast gap analyzer with auto-scheduling
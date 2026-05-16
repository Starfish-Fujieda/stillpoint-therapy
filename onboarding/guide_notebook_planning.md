# Onboarding Guide: Notebook Planning

This guide explains how to set up your NotebookLM notebooks — the clinical
knowledge base that grounds every therapy response in actual research and
clinical writing rather than LLM training data.

---

## Why NotebookLM?

When your AI therapist responds to something you say, it has two sources of
knowledge: its training data (broad but unfocused) and your notebooks (specific
and source-grounded). The notebooks win.

NotebookLM does something most RAG systems don't: it stays within its sources.
If you ask about a therapeutic technique and the relevant book is in the
notebook, you get a grounded answer. If the book isn't there, you get a clear
"I don't have a source for this" response rather than a confident fabrication.

This matters for therapy-adjacent work. The last thing you want is an AI
confidently making up clinical guidance.

---

## Structure Overview

Your knowledge base is organized into **topic notebooks**, not one big
notebook. Each notebook covers a clinical domain with 3-5 curated sources.

This structure has practical advantages:
- Faster, more focused responses (NotebookLM searches only the relevant notebook)
- Cleaner source attribution
- Easier to add or update a specific domain

### Minimum Required Notebooks (Everyone Gets These)

**1. Core Therapy Techniques**

Foundation for all other work. If you only set up one notebook, this is it.

What goes in it:
- ACT (Acceptance and Commitment Therapy) — the primary framework
- IFS (Internal Family Systems) — parts work and self-compassion
- General mindfulness and present-moment awareness
- Basic CBT concepts (optional)

Suggested sources:
- *The Happiness Trap* — Russ Harris (ACT, written for general readers)
- *No Bad Parts* — Richard Schwartz (IFS for general audience)
- *Get Out of Your Mind and Into Your Life* — Steven Hayes (ACT workbook)
- *Mindfulness in Plain English* — Bhante Gunaratana (meditation foundation)

**2. Self-Compassion & Shame Resilience**

Regardless of what brings you to this work, shame will be involved. This is
not a hypothesis — shame is the universal enemy of behavior change. Before
you can work on anything difficult, you need the framework to do it without
shame spiraling.

Suggested sources:
- *Self-Compassion: The Proven Power of Being Kind to Yourself* — Kristin Neff
- *I Thought It Was Just Me (But It Isn't)* — Brené Brown
- *The Mindful Path to Self-Compassion* — Christopher Germer
- *Fierce Self-Compassion* — Kristin Neff

---

## Tailored Notebooks

After the minimum two, the onboarding wizard interviews you about your
clinical landscape — what brings you to self-work, what patterns you've
noticed, what you want to change. From those answers, it proposes additional
notebooks.

Available topics (not exhaustive):

| Topic | When to create it |
|-------|------------------|
| CPTSD & Trauma | Developmental trauma, complex grief, repeated adverse experiences |
| ADHD & Executive Function | Diagnosed or suspected ADHD, chronic dysregulation of attention/time |
| ASD & Neurodivergence | Autistic experience, late-diagnosed or suspected ASD, masking |
| Anxiety & OCD | Generalized anxiety, social anxiety, OCD, health anxiety |
| Depression & Mood | Persistent low mood, anhedonia, bipolar (non-crisis) |
| Substance Use & Recovery | Alcohol, substance use, recovery support |
| Compulsive Sexual Behavior | Pornography, sexual compulsion, shame cycles |
| Grief & Loss | Bereavement, anticipatory grief, ambiguous loss |
| Relationship & Attachment | Attachment styles, relational patterns, couple dynamics |
| Anger & Emotional Regulation | Reactive anger, emotional flooding, dysregulation |
| Body Image & Eating | Disordered eating, body dysmorphia, food relationship |
| Digital Addiction | Social media, gaming, doom-scrolling compulsion |
| Sleep & Chronic Health | Chronic illness, sleep disorders, health anxiety |
| Identity & Life Transitions | Career transitions, parenthood, aging, cultural identity |

The wizard proposes which of these fit your situation. You decide which to
create. You can always add more later through Settings.

---

## Creating Notebooks in NotebookLM

After the wizard proposes your notebook topology, you create the notebooks
manually in NotebookLM (at notebooklm.google.com). This is the one step that
can't be automated — NotebookLM doesn't have an API for creating notebooks.

Steps for each notebook:
1. Go to notebooklm.google.com and click "New Notebook"
2. Name it exactly as the wizard suggests (e.g., "Core Therapy Techniques")
3. Add sources: upload PDFs, paste text, or add Google Drive links
4. Copy the notebook ID from the URL (the long alphanumeric string)
5. Paste the ID into the Stillpoint Settings page or directly into
   `config/therapist.yaml` under the relevant notebook entry

The notebook ID format looks like: `notebooks/abc123def456/...`
— you want the `abc123def456` part.

---

## Source Guidelines

**3-5 sources per notebook is the sweet spot.**

- Too few (1-2): shallow responses, gaps in coverage
- Too many (6+): diluted responses, slower queries, sources compete

**Prefer books over articles.**

Books have the depth and coherence for NotebookLM to build real understanding.
Articles are fine as supplements but shouldn't be the primary source.

**Use PDFs when you can.**

NotebookLM handles PDFs reliably. For sources you don't own digitally, many
publishers sell PDF editions; many books are available through library digital
lending (Libby, etc.).

**Don't duplicate across notebooks.**

If a book appears in two notebooks, NotebookLM treats the instances as
separate sources. This can cause inconsistency. Each book should live in its
most relevant notebook.

---

## After Setup

Once notebook IDs are in `config/therapist.yaml`, the session engine
automatically selects which notebooks to query based on what you're discussing.
You don't manage this manually.

You can check notebook coverage in the Settings page: it shows which notebooks
are configured, their status, and which topics they cover.

To add a new notebook later:
1. Create it in NotebookLM
2. Add sources
3. Go to Settings → Notebooks → Add Notebook
4. Enter the name, description, and ID

---

## A Note on the NotebookLM CLI

`scripts/setup.sh` installs the `notebooklm` CLI, which handles querying
notebooks during sessions. The CLI requires a one-time browser login
(`notebooklm login`) to authenticate with your Google account. This is
documented in the setup flow.

If you're running Stillpoint in Docker, the CLI cannot be used (browser
authentication is not available in containers). In that case, all responses
use the LLM's training data only, with an `[UNGROUNDED]` label.

# Onboarding Guide: Character Design

This guide walks you through designing your therapist persona — the AI
character you'll work with in Stillpoint sessions. Take your time with this.
The quality of the therapeutic alliance (how much you trust and feel
comfortable with the character) is the single strongest predictor of therapy
outcomes — more than modality, more than experience level.

Your guide through this process is **Eli** — a warm, clinically experienced
character who has no specific geographic location. Eli is defined by his
therapeutic presence: unhurried, curious, non-judgmental. His job is to help
you design *your* therapist. When onboarding ends, Eli steps back and your
custom therapist takes over.

---

## What You're Designing

You're creating a clinical profile that includes:

- A name (or first name only, or initials — your choice)
- A description: background, life experience, tone
- Clinical specializations (matched to your concerns)
- A communication style
- A therapeutic approach (default: ACT + IFS)

The result is a persona file that becomes the system prompt for all sessions.
You can edit it later via Settings, or redo the onboarding at any time.

---

## The Five Design Factors

Research on therapist matching identifies these evidence-based factors. The
onboarding wizard covers each one. This guide explains the reasoning.

### 1. Identity Matching

Studies consistently show that clients benefit when they feel their therapist
understands their cultural or experiential context — not necessarily shares it,
but genuinely *gets* it.

Consider:

- **Gender**: Do you want a therapist of the same gender, a different gender,
  or does it not matter? There's no right answer. Some people find same-gender
  therapists easier to open up to; others prefer cross-gender. Some topics feel
  different depending on this dynamic.

- **Cultural background**: Do you want someone from a shared cultural context?
  This is especially relevant if culture, immigration, or ethnic identity is
  part of what brings you to self-work.

- **Age proximity**: A therapist described as roughly your age feels like a
  peer. An older figure feels like a mentor. A younger figure might feel
  easier to contradict. Which dynamic serves you best?

- **Life experience overlap**: Recovery, parenthood, being an expat, LGBTQ+
  experience, neurodivergence — if any of these are central to your work, you
  may want a therapist who explicitly "gets it" from lived experience.

You don't have to specify all of these. Unspecified dimensions default to
neutral (the persona won't mention them).

### 2. Communication Style

This is how your therapist *talks*. The differences matter more than they might
seem — you'll be receiving this style in every session.

| Dimension | Option A | Option B |
|-----------|----------|----------|
| Tone | Direct / challenging | Gentle / unhurried |
| Structure | Agenda-driven | Follows your lead |
| Humor | Uses it lightly | Doesn't use it |
| Mode | Asks questions | Offers interpretations |
| Register | Casual | Professional |

You can mix and match. Most people want something in the middle (gentle but not
soft, structured but not rigid). The wizard will ask you directly.

### 3. Specialization Alignment

Your therapist should have credible expertise in the areas relevant to your
work. During the clinical landscape interview, you'll describe what brings you
here. The wizard maps those concerns to specializations.

Examples:
- Anxiety, OCD → specialization in anxiety and nervous system regulation
- CPTSD, attachment wounds → trauma specialty, parts work
- ADHD, executive dysfunction → neurodivergence-informed approach
- Grief → loss and transition specialist

Specializations affect how the persona introduces itself, how it frames
problems, and which NotebookLM notebooks get queried during sessions.

### 4. Therapeutic Approach

The default is **ACT + IFS** — Acceptance and Commitment Therapy integrated
with Internal Family Systems. This is the framework the entire system is built
around. Unless you have a strong preference otherwise, keep the default.

If you have prior therapy experience with a different modality and want to
build on that, you can request:

- **CBT** (Cognitive Behavioral Therapy)
- **DBT** (Dialectical Behavior Therapy, especially useful for emotional
  dysregulation)
- **Psychodynamic** (relational, insight-oriented)
- **Somatic** (body-based awareness — note: requires good interoception)

Specifying an approach affects how the therapist frames problems and which
sources get prioritized in your notebooks.

### 5. Therapeutic Alliance Feel

Beyond specifics: what does safe, understood, and not-judged feel like for
you?

Some people need warmth above all — a therapist who is explicitly kind and
validating before anything challenging is introduced. Others find too much
warmth feel patronizing; they want intellectual engagement, directness, and
to be treated as capable.

The wizard's final question will ask you to describe the best therapeutic
conversation you can imagine. That answer is used to tune the persona in ways
that don't fit into any checkbox.

---

## What Happens After

Once character design is complete, the wizard uses your answers to generate:

- `personas/therapist.md` — The full clinical profile (what becomes the system
  prompt). You can read and edit this file directly.
- `config/therapist.yaml` — Configuration: name, specializations, LLM
  settings, notebook IDs.

You can run the onboarding wizard again at any time to regenerate these files.
If you want to make minor tweaks, edit the files directly — they're plain text.

---

## Tips

- **Don't overthink the name.** The name mainly affects how the persona feels
  to you. "Dr. Sarah" and "Marco" will behave identically if everything else
  is the same.
- **The wizard generates a complete profile from minimal input.** You don't
  have to have strong opinions about every dimension. Describe what you can;
  the wizard fills in clinically sensible defaults.
- **You can change it.** The persona is not permanent. If three sessions in
  you realize the communication style isn't working, update the profile.
- **The persona is not a friend.** The character will be warm and present, but
  it's designed to maintain appropriate therapeutic boundaries — not to chat
  or socialize. This is intentional.

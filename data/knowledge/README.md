# Static Knowledge Base

> **DRAFT — NOT YET REVIEWED.** This directory contains draft content for the
> static knowledge base fallback (active when NotebookLM grounding is
> unavailable). All content requires clinician or trained peer review before
> merge. See `data/knowledge/README.md` (this file) for the review process.

## Purpose

This directory provides a **fallback** for when the primary knowledge grounding
mechanism (NotebookLM) is not configured or not reachable. It is **not** a
substitute for live grounding — it is a safety net that allows the therapist
to respond with established, well-known clinical concepts at a lower level
of specificity than the user would get from a configured NotebookLM setup.

Every response drawn from this directory is tagged so the user can see at a
glance what weight to give it. **Until a topic passes clinical review** the
tag reads
`[FALLBACK — draft static content, not yet clinically reviewed (topic: act_basics)]`
— it deliberately does **not** claim "grounded," because clinical sign-off
has not happened (even though the inline citations are now verified, see the
two-tier format below).

Once a topic passes clinician/peer review AND every `[verified book-level; …]`
citation has been finalized to a real locator by a reviewer with the physical
book, its tag is promoted in `stillpoint/knowledge.py::_query_static_knowledge()`
to a grounded form (e.g., `[GROUNDED — static knowledge base, source: act_basics]`).
That promotion is the gate — the tag must not overstate the content's review
state. Placeholder resolution alone is not sufficient; clinical sign-off is.

## When this content is used

`stillpoint/knowledge.py::query_knowledge()` first attempts to ground via
NotebookLM. If that returns `[UNGROUNDED]` (no notebooks configured, all
queries fail, or no binary on PATH), it then attempts to ground via the
static knowledge base. If the static base is also unable to match, the
function returns `[UNGROUNDED]` as before.

The static base can be disabled entirely by setting
`STILLPOINT_STATIC_KB=false` in the environment.

## File format

Each topic file is a standalone markdown document with:

1. **Title and status header.** First line is `# <Topic Name>`. Second line is
   a status note (`> **DRAFT — NOT YET REVIEWED.** ...`) until the content
   passes review.
2. **Keywords line.** A line near the top of the form `keywords: foo, bar, baz`
   is used by the keyword-based topic selector. Lowercase, comma-separated.
3. **Safety framing.** Every file includes a "When this approach is not
   appropriate" section listing contraindications and when to seek human help.
4. **Inline citations.** Every factual claim carries an inline citation in
   one of two verified forms:
   - `[verified source: Author Year — *Title*, Ch. X]` — **passage-confirmed.**
     The cited passage was returned by NotebookLM (when the book is an
     uploaded source) or is a web-confirmed journal article. This is the
     strongest tier; chapter/locator is real.
   - `[verified book-level; exact page pending reviewer — Author Year,
     *Title*, Ch. X]` — **book-confirmed, page not.** The book, author, year,
     and publisher are verified (web source), but the specific chapter/page
     was NOT independently confirmed because the book is not in NotebookLM.
     A reviewer with the physical book must finalize the locator.
   - Do NOT write `[source: …]` or invent page numbers. An unverified
     locator is worse than an honest book-level tag. While drafting, mark
     unknowns `[CITATION NEEDED — …]`; resolve them into one of the two
     verified forms before merge.
5. **Scope disclaimer.** Each file ends with a reminder that this is a
   fallback, not a substitute for live grounding or human therapy.

## Review process

Before any topic file can be merged:

1. **Self-review by the author.** Confirm every claim is supported by the
   cited source. Resolve every `[CITATION NEEDED]` placeholder into one of
   the two verified forms above: prefer `[verified source: …]` (passage-
   confirmed via NotebookLM or a journal article); fall back to
   `[verified book-level; …]` only when the book is not available to query.
   For book-level tags, verify the book/author/year/publisher against a real
   web source — do not trust memory (past drafts have shipped wrong authors,
   titles, and years).
2. **Clinician or trained peer review.** A second person with clinical
   training (therapist, counselor, peer-reviewed researcher) reads the file
   end-to-end. Focus areas:
   - Accuracy of paraphrased concepts
   - Citation correctness (does the source actually support the claim?)
   - Safety framing completeness (are contraindications listed?)
   - Wording for users in distress (does it point to human help where needed?)
3. **Status header update.** After review, the file's status header changes
   from `DRAFT — NOT YET REVIEWED` to `Reviewed: <date>, <reviewer name>`.
4. **PR description.** The PR that adds the file notes the review status and
   the reviewer's name.

## Topics in this directory

### Current

- `act_basics.md` — ACT (Acceptance and Commitment Therapy) six core
  processes, with emphasis on defusion, acceptance, values, and committed
  action. Lower-risk foundation topic; chosen over self-compassion because
  the Self-Compassion notebook documents a "backdraft" risk for trauma
  survivors (see deferred topics below).
- `intrusive_thoughts.md` — The intrusive-thoughts-vs-intent distinction
  and thought-action fusion. Transdiagnostic — applies across OCD,
  anxiety, depression, PTSD, and general mental wellness. Chosen for
  PR 1 because the ACT/IFS notebook identifies it as a "primary grounding
  skill."

### Deferred (not in PR 1)

- `self_compassion.md` — Neff's three-component model, Brown's shame
  resilience framework. **DEFERRED** because self-guided self-compassion
  practice carries specific failure modes for trauma survivors:
  - "Backdraft" — feelings of warmth can reactivate painful attachment
    memories for survivors of abuse (Neff, Gilbert)
  - "Stage-skipping" / retraumatization — exploring shame work before
    establishing internal safety
  - "Verbal self-flagellation" — "verbal ventilation" can shift into
    self-attack without a witness
  - "Premature forgiveness" — pressure to "forgive and forget" mimics
    denial
  - "Mistake-rumination trap" — self-punishment loop disguised as
    problem-solving
  When planned, this content must include explicit backdraft warnings,
  contraindication lists, and a stabilization-first gate. See
  `~/.claude/plans/enumerated-petting-wombat.md` PR 3 section for
  requirements.
- `ifs_parts.md` — IFS parts language (managers, firefighters, exiles,
  Self-energy). Useful but adds complexity; better as a follow-up.
- `stabilization.md` — Stage-one stabilization techniques (grounding,
  resourcing, window of tolerance). Often prerequisite to deeper work;
  high-value but content-heavy.

### Topics considered and rejected for PR 1

- Body-based / somatic interventions. Per the ASD/ADHD/CPTSD clinical
  literature, somatic questions are neurologically inaccessible for some
  users. Excluded.
- "How to stop thinking about X" type instructions. Per ACT, struggling
  with thoughts amplifies them. The intrusive-thoughts file already
  covers this; a separate "thought suppression" file would be redundant
  and potentially harmful.

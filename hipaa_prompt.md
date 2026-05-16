# HIPAA PHI Scanning Prompt

Use this prompt before sharing any Stillpoint session report or data export
with a human therapist, healthcare provider, or any third party.

Stillpoint keeps all data local and never transmits sessions automatically.
However, **session notes you write** may contain identifiable information
without you realizing it. This scan catches that before you share.

---

## How to Use

1. Export the data you want to share (report, session notes, or config file).
2. Copy the export into your preferred LLM (Claude, ChatGPT, Gemini, etc.).
3. Paste the prompt below, followed by your data.
4. Review the findings and redact before sharing.

---

## Scanning Prompt

Paste this into your LLM session, followed by the text you want to scan:

---

```
You are a HIPAA PHI (Protected Health Information) compliance reviewer.
Your task is to identify all potential PHI in the text below and suggest
redactions. Do not summarize the content — only flag identifiers.

HIPAA defines 18 categories of PHI. Check for ALL of the following:

1. Names — Full names, first names alone if combined with other identifiers,
   nicknames that could identify a person.

2. Geographic data — Street addresses, city+state combinations, ZIP codes,
   county, precinct, and any geographic subdivision smaller than a state.
   Note: The first 3 digits of a ZIP code are usually safe; full ZIPs are not.

3. Dates (except year) — Birth dates, admission dates, discharge dates,
   death dates, and ages over 89 years. Relative dates (e.g., "last Tuesday")
   are safe if they can't be anchored to a specific calendar date.

4. Phone numbers — All telephone and fax numbers.

5. Fax numbers — All fax numbers.

6. Email addresses — Any email address.

7. Social Security numbers — Full or partial SSNs.

8. Medical record numbers — Any ID assigned by a healthcare provider.

9. Health plan beneficiary numbers — Insurance member IDs.

10. Account numbers — Bank accounts, credit card numbers, or any financial
    account identifiers.

11. Certificate/license numbers — Driver's license, professional license,
    medical license numbers.

12. Vehicle identifiers — License plate numbers, VINs, or vehicle serial
    numbers.

13. Device identifiers — Serial numbers for medical devices, implants, or
    wearables.

14. Web URLs — Any URL that could identify a person or their account
    (e.g., a personal blog, a social profile URL).

15. IP addresses — IPv4 or IPv6 addresses.

16. Biometric identifiers — Fingerprint data, retinal scans, voice prints,
    or other biometric descriptors.

17. Full-face photos or comparable images — Descriptions that would allow
    visual identification.

18. Any other unique identifier — Anything not listed above that could
    reasonably be used alone or in combination to identify a specific person.

---

For each item you find:
- Quote the exact text
- Label which PHI category it falls into
- Suggest a replacement (e.g., "[REDACTED]", "[CITY]", "[DATE]")

After reviewing all 18 categories, provide a short summary:
- How many PHI items were found
- Severity assessment: safe to share / share with redactions / do not share
- Any patterns (e.g., the same person's name appears throughout)

If you find no PHI, say so explicitly. Do not guess or fabricate findings.

---

TEXT TO SCAN:

[PASTE YOUR EXPORT HERE]
```

---

## After the Scan

- Replace flagged identifiers with placeholders like `[NAME]`, `[DATE]`, `[CITY]`.
- For session reports shared with a therapist: the therapist already knows your
  name, so `[NAME]` references to yourself are usually fine to keep. Redact
  names of third parties (family members, colleagues, partners).
- Save the redacted version separately before sharing.

## What Stillpoint Stores Locally

| Data | Location | Notes |
|------|----------|-------|
| Session notes (raw) | `~/.stillpoint/palace/` | Vector store, local only |
| Config files | `config/` | YAML, gitignored |
| Personas | `personas/` | Markdown + JSON, gitignored |
| Generated reports | Wherever you save them | You control distribution |

Nothing is transmitted to any server by Stillpoint itself. LLM API calls
send only the in-session conversation to your chosen provider (Anthropic,
OpenAI, etc.) under their standard privacy policies.

## Resources

- [HHS HIPAA Safe Harbor Method](https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/index.html)
- [18 PHI Identifiers — HHS reference](https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html)

# GOVERNANCE
Purpose: master index of the files that govern how this repo is built and changed.
Last updated: 2026-09-28

**Rule: before any task, read PREFLIGHT.md; after any task, complete POSTFLIGHT.md.**

Governance files live in `/docs` to keep the repo root clean for Streamlit Cloud (`streamlit_app.py`, `requirements.txt`).

| File | Purpose | Read when | Update when |
|---|---|---|---|
| [PREFLIGHT.md](PREFLIGHT.md) | Checklist run before touching code | Start of every task | Checklist itself changes |
| [POSTFLIGHT.md](POSTFLIGHT.md) | Verification gate before a task is "done" | End of every task | Checklist itself changes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Map of modules, data flow, boundaries | Any task touching structure | Structure changes |
| [CONVENTIONS.md](CONVENTIONS.md) | How code is written | Any code task | A rule is added or changed |
| [DECISIONS.md](DECISIONS.md) | Append-only ADR log | Before revisiting a past choice | Every non-trivial technical or methodological choice |
| [TESTING.md](TESTING.md) | Test strategy and what "verified" means | Any code task | Test approach changes |
| [LESSONS.md](LESSONS.md) | Mistakes, root causes, rules adopted | PREFLIGHT | Every mistake or insight |
| [CHANGELOG.md](CHANGELOG.md) | Reverse-chronological change record | When reviewing history | Every meaningful change |
| [DATA_SOURCES.md](DATA_SOURCES.md) | Every input file: source, vintage, known issues | Any data task | A source is added, replaced or found flawed |
| [METHODOLOGY.md](METHODOLOGY.md) | Model, scoring, cost and optimizer method in plain language | Any modeling task | Method changes |

Standing rules:
- Preflight before work, postflight after. No exceptions for non-trivial changes.
- Every non-trivial decision goes to DECISIONS.md, every meaningful change to CHANGELOG.md, every mistake to LESSONS.md.
- If something is ambiguous or under-specified, stop and ask the owner (Pat) rather than assume. When working unattended, take the most reasonable reading, log it as an ADR with status `proposed`, and flag it.
- Keep governance current. Stale governance is worse than none.
- Every number shown to a user traces to a source in DATA_SOURCES.md or an assumption in METHODOLOGY.md.

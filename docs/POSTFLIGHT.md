# POSTFLIGHT
Purpose: verification gate run after code changes and before declaring a task done.
Last updated: 2026-09-28

A task is not done until every applicable box is checked.

- [ ] Tests written for new logic and `pytest -q` passes (TESTING.md).
- [ ] Pipeline re-run if data or model code changed (`python scripts/run_pipeline.py`), and outputs spot-checked.
- [ ] Conventions followed (`ruff check .` clean).
- [ ] CHANGELOG.md updated.
- [ ] New decisions logged to DECISIONS.md.
- [ ] New mistakes or insights logged to LESSONS.md.
- [ ] ARCHITECTURE.md updated if structure changed.
- [ ] DATA_SOURCES.md / METHODOLOGY.md updated if inputs or method changed.
- [ ] Work committed with a conventional commit message.

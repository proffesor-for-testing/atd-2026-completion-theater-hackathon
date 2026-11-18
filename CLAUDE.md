# Session Seat Desk: Completion Theater Hackathon (ATD 2026)

Seat-reservation app for two fictional workshops: JSON API + basic UI + durable SQLite. 60-minute build, then a cross-audit by another team. Judged on 8 ACs observed against the frozen commit (40 pts), evidence (30), audit (20), creativity (10). Simple and working beats clever.
Requirements: `docs/acceptance-criteria.md` (AC-01…AC-08). Sources: `docs/01-Starter-PRD.md`, `docs/api-contract.md`.

## Commands (run from `starter-python/`, Python 3.11+, stdlib only, no pip)
```
install:          none (python ../tools/preflight.py checks the runtime)
reset:            python app.py --reset      # fixture only; NEVER on ordinary start
run:              python app.py              # http://127.0.0.1:8765, env PORT / DATA_DIR
test (all):       python -m unittest discover -s tests -t . -v
test (acceptance):python -m unittest discover -s tests/acceptance -t . -v
lint:             python -m compileall -q .
verifier:         see tools/README.md (uses adapter.json)
```
On Windows `python` may be `py -3`. Root `tests/` is CI for the organizer's helper tools; it is not app tests. Don't touch it.

## Non-negotiables
1. **ATDD:** no production code without a failing acceptance test for an AC first. See `atdd-workflow`.
2. **Red never lands:** never push with failing tests, except a new AC's red test pushed together with its green fix. See `git-workflow`.
3. **Done means demoable:** an AC is done only when it meets `definition-of-done`.
4. **No theater:** never show or return success before the DB commit; never return 200 with an error; never fake counts. Readback must match storage.
5. **Durable + isolated:** all state in SQLite under `DATA_DIR`; reset only via `--reset`; no in-memory state.
6. **Secrets/real data stay out:** fictional aliases only; no `.env`, tokens or real attendees in git.
7. **Scope:** build only what an AC asks for. Record ideas as stretch goals, not code.
8. **Ambiguity:** pick the simplest interpretation, add it under `## Assumptions`, keep going.
9. **Freeze:** at 21:55 CET commit + push, record the full SHA, stop pushing. See `git-workflow`.

## Layout
```
starter-python/            # declared app dir (frozen + judged)
  app.py                   # HTTP server, routes, SQLite access
  sessions.json            # seed: CT-101 cap 2, CT-102 cap 3
  (UI is server-rendered in app.py: render_page)
  adapter.json             # verifier start/reset/field mapping; keep in sync
  tests/support.py         # RunningApp: real subprocess, temp DATA_DIR, free port
  tests/acceptance/        # test_acNN_<slug>.py, one file per AC
  tests/unit/              # only for branchy logic (validation, idempotency rules)
docs/acceptance-criteria.md
```

## Project skills (load when relevant)
| Skill | Use when |
|---|---|
| `atdd-workflow` | starting any AC or feature, or writing or fixing tests |
| `coding-standards` | writing or reviewing production code in this repo |
| `git-workflow` | committing, pulling, pushing, resolving conflicts, freezing |
| `definition-of-done` | before marking an AC done, before freeze or the demo |
| `score-hackathon` | facilitator judging only (pre-existing, organizer's) |

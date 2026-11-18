---
name: coding-standards
description: Project-specific coding conventions for this Python stdlib + SQLite repo: where code goes, how errors, validation, state and concurrency are handled. Use it whenever you write, move or review production code in starter-python/, so code written in parallel by teammates stays consistent and merges cleanly.
---

# Coding standards (Python 3.11+ stdlib, `http.server` + `sqlite3`)

No dependencies: the frozen app must start on an auditor's laptop with no `pip install`. Lint is `python -m compileall -q .` (syntax only), so these rules carry the weight.

## Where code goes
- `starter-python/app.py` holds the routes in `Handler.do_GET` / `do_POST`. Keep each route as a small `if` branch that calls a plain function.
- If `app.py` grows past ~250 lines, split it into `store.py` (all SQL and transactions; no HTTP types) and keep `app.py` for HTTP and validation. Agree on the split before two people edit at once.
- The UI is server-rendered HTML built from the same store functions as `/sessions` (assumption A-01). Use one function to read sessions with counts, shared by the API and the UI, so they cannot disagree.

## Conventions
- **Errors:** return 4xx with `{"error": {"code": "CAPACITY_FULL", "message": "No remaining seats"}}` via `json_response`. Codes: `INVALID_JSON`, `INVALID_INPUT`, `UNKNOWN_SESSION`, `NOT_FOUND`, `CAPACITY_FULL`, `KEY_CONFLICT`. Never send 200 with an error, and never leak tracebacks. Catch exceptions per request so the process stays up (AC-08).
- **Validation:** validate at the edge before touching the DB. The body must be a JSON object; `attendeeAlias` is a str that is non-blank after `.strip()`; `requestKey` is a non-empty str; `sessionId` must exist.
- **State:** SQLite at `DATA_DIR/seats.db` only. Open a connection per request; never cache counts in memory. Compute `activeCount` with `COUNT(*) ... WHERE status='active'` and `remainingSeats = capacity - activeCount`.
- **Concurrency:** do every reserve or cancel as a single `BEGIN IMMEDIATE` transaction: look up the key, check capacity, then insert. The server is threaded, so check-then-insert outside a transaction will oversell (AC-04). Use `isolation_level=None` and explicit `BEGIN IMMEDIATE`/`COMMIT`, plus `timeout=10` on `connect`.
- **Idempotency:** `request_key` is UNIQUE globally. On an existing key, a match on the same session and the same trimmed alias returns the stored row (whatever its current status); anything else returns 409 `KEY_CONFLICT`.
- **IDs:** `uuid.uuid4().hex`, generated once at insert.
- **Config:** env vars only, read at the top of `app.py`: `PORT`, `DATA_DIR`, `HOST` (default `127.0.0.1`; Docker sets `0.0.0.0`). Never reset on start.
- **Field names:** use contract names exactly (`sessionId`, `attendeeAlias`, `requestKey`, `activeCount`, `remainingSeats`). If you change one, update `adapter.json` in the same commit.
- **Naming:** test methods are `test_acNN_<behaviour>`, e.g. `test_ac05_replay_same_key_returns_original_id`.

## Keep it small
- No abstractions for a second use case that doesn't exist yet. Duplicating code once is fine within a time box.
- No new dependencies; stdlib only.
- Leave no dead code, commented-out blocks or TODOs without an AC ID.

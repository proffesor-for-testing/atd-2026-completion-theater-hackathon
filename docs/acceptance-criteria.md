# Acceptance criteria

Source: `docs/01-Starter-PRD.md` (rules v1.1) and `docs/api-contract.md`; README links them. IDs match the PRD and are permanent. Each AC = 5 of the 40 working-app points.
Status: `todo` → `red` (test written, failing) → `done` (meets definition-of-done).
App dir: `starter-python/`. Tests: `starter-python/tests/acceptance/`.

| ID | Behaviour (observable) | Source (PRD wording) | Status | Test |
|---|---|---|---|---|
| AC-01 | After `--reset` + start, GET `/` returns HTML listing CT-101 "Catching Ghost Databases" and CT-102 "Tests That Can Fail"; no account or hidden service needed. | "opens the UI and sees the two seeded sessions. App startup does not require the builder's account or a hidden service." | done | `tests/acceptance/test_ac01_clean_start_and_ui.py` |
| AC-02 | GET `/sessions` → 200 `{"sessions":[{id,title,capacity,activeCount,remainingSeats}]}`; fresh: counts 0, remaining 2 and 3. UI shows the same numbers. | "GET /sessions returns both IDs, capacities, active counts and remaining seats … The UI agrees with this response." | done | `tests/acceptance/test_ac02_session_readback.py` |
| AC-03 | POST `/reservations` `{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}` → 2xx `{id,sessionId,attendeeAlias,requestKey,status:"active"}`; GET `/reservations/{id}` returns the same record; CT-101 remaining = 1 in API and UI. | "returns success with a stable reservation ID and active status … Remaining CT-101 seats become 1 and the UI reflects that state." | done | `tests/acceptance/test_ac03_reservation.py` |
| AC-04 | Third distinct CT-101 request after two active → 4xx `{"error":…}` capacity error, no row created. 10 concurrent distinct requests on a one-seat-left state → exactly 1 success, activeCount 2. | "a third distinct request returns a non-success response with a clear capacity error and creates no reservation … exactly one success" | done | `tests/acceptance/test_ac04_capacity.py` |
| AC-05a | Replay of same key + same session + same trimmed alias → same ID and current status, no extra seat used. | "Repeating the same key, same session and same trimmed alias returns the original reservation ID" | done | `tests/acceptance/test_ac05_idempotency.py` |
| AC-05b | Same key with a different session or alias → 4xx conflict, no state change. Keys are globally unique. | "Reusing that key with a different session or alias returns a conflict with no state change." | done | `tests/acceptance/test_ac05_idempotency.py` |
| AC-06 | POST `/reservations/{id}/cancel` `{}` → cancelled record, releases one seat; repeat cancel → same cancelled record, count unchanged; replaying the original create → same cancelled record (never reactivates). | "Cancelling an active reservation releases exactly one seat … must not reactivate it." | done | `tests/acceptance/test_ac06_cancellation.py` |
| AC-07 | Create one active + one cancelled, stop process, start without reset → same IDs, statuses, counts via fresh HTTP and UI. | "stop the process, start it again without reset, and use fresh HTTP requests plus the UI" | done | `tests/acceptance/test_ac07_durable_state.py` |
| AC-08 | Unknown session, blank/whitespace alias, missing/empty requestKey, malformed JSON, cancel unknown ID → 4xx with non-empty `error`; counts unchanged; server still answers afterwards. | "produce non-success responses with clear errors. None may change reservation counts … The process stays available afterward." | done | `tests/acceptance/test_ac08_invalid_input.py` |

## Assumptions
Interpretations made where the PRD is ambiguous. Change them freely, but update the affected test as well.

- A-01 (AC-01/02/03/07): The UI is server-rendered HTML from the same SQLite state (plus plain `<form>` posts or a small fetch script). This lets the stdlib tests observe "UI agrees" without a browser. If you switch to a JS-rendered page, the AC-01 test must change to check the page's data source.
- A-02 (AC-04/08): Status codes: 201 create, 200 replay/read/cancel, 400 invalid input or malformed JSON, 404 unknown session/reservation, 409 capacity full and key conflict. Errors are `{"error":{"code","message"}}`, which matches the contract. Keep `adapter.json` in sync.
- A-03 (AC-05): The alias is stored trimmed. The replay comparison uses the trimmed alias and is case-sensitive.
- A-04 (AC-04): Concurrency is handled by doing check-and-insert in one SQLite `BEGIN IMMEDIATE` transaction per request.
- A-05 (AC-08): `attendeeAlias` is at most 30 characters after trimming; longer is 400 `INVALID_INPUT` ("attendeeAlias must be at most 30 characters"). The UI field has `maxlength="30"`. The cancellation confirmation in the UI is styled red (`message-cancelled`), but it stays `role="status"` because it is not an error.

## Out of scope / stretch
- Waitlists, search, accessibility beyond the basic labels/keyboard/visible errors, evidence views (PRD: only after all 8 ACs).
- Auth, payments, messaging, public hosting, AI features in the app.
- Reset HTTP endpoint (optional; never public). Use `python app.py --reset`.

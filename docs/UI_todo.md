# UI to-do: Session Seat Desk

Work through these in order. Each UI step is a test-first cycle: write a failing test, run it, commit, make it pass, commit. Tick a box in the same commit as the code.

## Needs a ruling first

- [x] Rule on AC-09 (visible error messages in the UI). Ruled 'unblock them' (loop-questions.md); items 11 and 12 are open.

## UI build (test-first, one commit per step)

- [x] Reservation form (session, alias, request key) that posts to `POST /reservations`
- [x] Seat counts load from `GET /sessions` and refresh after each action
- [x] Cancel control per reservation, posting to `/reservations/{id}/cancel`
- [ ] AC-02: UI counts agree with `GET /sessions` (acceptance test on the page)
- [ ] AC-03: remaining CT-101 seats drop to 1 in both `/sessions` and the UI
- [ ] AC-03: unknown `GET /reservations/{id}` returns a 4xx JSON error (test not yet written)
- [ ] AC-08: the process stays available after each rejected request
- [ ] Reservation IDs and request keys are unique across sessions (domain rule)
- [ ] AC-01: README steps start the app from a clean copy and open the UI
- [x] AC-09 (after ruling): visible, dismissable error messages in the UI
- [ ] AC-09 (after ruling): after a failure the UI still accepts actions and its counts match `/sessions`

## Housekeeping

- [ ] Stop the background server on port 8765 (`pkill -f "python3 app.py"`) before running tests or resetting state
- [ ] Review uncommitted changes (`AGENTS.md`, `docs/`, `starter-python/pytest.ini`, `starter-python/tests/`, deleted `starter-python/test_app.py`) before the first new commit

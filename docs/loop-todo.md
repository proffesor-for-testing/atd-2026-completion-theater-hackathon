# Loop to-do: Session Seat Desk

Each `/loop` run takes the first `- [ ]` line that isn't marked blocked, does one red-green cycle for it, and ticks it `- [x]` in the same commit as the code. Add a line for any new step you find, below the step it depends on. Only the runs change this file.

Steps are in order. Each one is a single test-first cycle.

## Done (for reference)

- [x] Storage: atomic JSON save and load, missing file, corrupt file (`starter-python/storage.py`)
- [x] UI: `render_page` shows seeded sessions; `GET /` serves it (AC-01 UI part)
- [x] `GET /sessions` readback with counts and remaining seats (AC-02)
- [x] Corrupt state file reported as `STATE_CORRUPT` (integration)

## Open

- [ ] AC-01: README starts the app from a clean copy and opens the UI, with no builder account needed
- [ ] AC-02: UI counts agree with `GET /sessions` (acceptance test on the page)
- [x] AC-03: `POST /reservations` creates an active reservation for CT-101 with a stable ID
- [x] AC-03: `GET /reservations/{id}` returns the stored record, or 4xx if unknown
- [ ] AC-03: `GET /reservations/{id}` with an unknown ID returns a 4xx JSON error (test not yet written)
- [ ] AC-03: after a reservation, remaining CT-101 seats drop to 1 in `GET /sessions` and the UI
- [x] AC-04a: a third distinct CT-101 request is rejected with a clear capacity error and creates no reservation
- [x] AC-04b: concurrent distinct requests on a one-seat state give exactly one success and active count 2
- [x] AC-05: same key, session and alias returns the original reservation without using another seat
- [x] AC-05: a replay whose alias differs only by surrounding spaces returns the original reservation
- [x] AC-05: same key with a different session or alias returns a conflict and changes no state
- [x] AC-06: cancelling an active reservation releases exactly one seat
- [x] AC-06: repeated cancellation reports cancelled and leaves the count unchanged (ruled covered)
- [x] AC-06: replaying the original request after cancellation returns the cancelled record and does not reactivate it (ruled done)
- [x] AC-07: active and cancelled reservations survive a restart without reset, read back over HTTP (covered by user ruling; the restart probe passed before any code change)
- [x] AC-08: malformed JSON returns a 400 JSON error with no state change
- [x] AC-08: a body missing `attendeeAlias` or not a JSON object returns a 400 JSON error with no state change and no dropped connection
- [ ] AC-08: unknown reservation cancel returns a 4xx JSON error with no state change (test not yet written)
- [ ] AC-08: the process stays available after each rejected request
- [x] AC-08 (left after blank alias): unknown session and missing `requestKey` return a 4xx JSON error instead of dropping the connection
- [x] Reject blank or whitespace-only aliases and trim before comparing (domain rule)
- [ ] Reservation IDs and request keys are unique across sessions (domain rule)
- [ ] (blocked: needs a ruling on AC-09 first) AC-09: a failed action or storage problem shows a visible error in the UI, dismissed by the user or replaced by the next success
- [ ] (blocked: needs a ruling on AC-09 first) AC-09: after a failure the UI still accepts actions and its counts match `GET /sessions`

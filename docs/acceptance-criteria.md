# Acceptance criteria: Session Seat Desk

Source: [Starter PRD](01-Starter-PRD.md) and [API contract](api-contract.md), rules version 1.1. This file is the working copy the team builds and tests against. If it disagrees with the PRD, the PRD wins and this file gets corrected.

Each criterion is worth 5 of the 40 working-app points. Only an executed PASS counts.

## Acceptance criteria

| ID | Requirement and observable acceptance |
| --- | --- |
| AC-01 | **Clean start and UI.** Another team follows the README, starts the app from the submitted source, opens the UI and sees the two seeded sessions. App startup does not require the builder's account or a hidden service. |
| AC-02 | **Session readback.** `GET /sessions` returns both IDs, capacities, active counts and remaining seats. On fresh reset, counts are 0 and remaining seats are 2 and 3. The UI agrees with this response. |
| AC-03 | **Reservation.** A valid request for CT-101 with alias Ada and key K1 returns success with a stable reservation ID and active status. `GET /reservations/{id}` returns the same record. Remaining CT-101 seats become 1 and the UI reflects that state. |
| AC-04 | **Capacity.** After two active CT-101 reservations, a third distinct request returns a non-success response with a clear capacity error and creates no reservation. A fresh one-seat state with simultaneous distinct reservation attempts must produce exactly one success and an active count of 2; all other attempts must reject without state changes. The shared helper repeats ten bounded batches of ten attempts. This probes races; it does not prove absence of all concurrency defects. |
| AC-05 | **Idempotency.** Repeating the same key, same session and same trimmed alias returns the original reservation ID and current status without consuming another seat. Reusing that key with a different session or alias returns a conflict with no state change. Request keys are globally unique, not just unique within a session. |
| AC-06 | **Cancellation.** Cancelling an active reservation releases exactly one seat. Repeating cancellation reports cancelled status and leaves the count unchanged. Replaying its original reservation request after cancellation returns that same cancelled reservation; it must not reactivate it. A new request key is needed for a new reservation. |
| AC-07 | **Durable state.** After creating one active and one cancelled reservation, stop the process, start it again without reset, and use fresh HTTP requests plus the UI to read the same IDs, statuses and seat counts. Refreshing a browser alone is not a restart. |
| AC-08 | **Invalid input.** Unknown session, blank alias, missing request key, malformed JSON and cancelling an unknown reservation produce non-success responses with clear errors. None may change reservation counts or remaining seats. The process stays available afterward. |

Sub-checks used by the verification checklist: AC-04a is the sequential capacity case; AC-04b is the concurrent case. AC-04 needs both.

## Seed data

Seeded on an explicit fresh reset only. Restart must not reset them.

| Session ID | Title | Capacity | Initial active reservations |
| --- | --- | --- | --- |
| CT-101 | Catching Ghost Databases | 2 | 0 |
| CT-102 | Tests That Can Fail | 3 | 0 |

## Domain rules

- A reservation has: generated stable ID, session ID, attendee alias, caller-supplied request key, status (`active` or `cancelled`).
- Remaining seats = capacity minus active reservations.
- Aliases: reject blank or whitespace-only. Trim before comparing repeat requests. Otherwise case-sensitive.
- Request key: must be a non-empty string.

## API (fixed paths)

| Method and path | Input | Minimum result |
| --- | --- | --- |
| `GET /sessions` | none | session IDs, titles, capacities, active counts, remaining seats |
| `POST /reservations` | `sessionId`, `attendeeAlias`, `requestKey` | stable reservation ID, session, alias, key, status |
| `GET /reservations/{id}` | ID from a successful response | stored reservation, or 4xx if unknown |
| `POST /reservations/{id}/cancel` | `{}` | current cancelled record, or 4xx if unknown |

Example request: `{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}`

Response shapes and error forms are in the [API contract](api-contract.md). Errors are a 4xx status with a non-empty JSON `error`. A 200 response carrying an error is a failure.

## Invariants

- Active count never exceeds capacity; remaining seats never go below 0.
- Replays, rejected input and repeated cancellation create no extra state changes.
- A successful response agrees with independent stored-state readback.
- Restart preserves records and counts.
- Test failure reaches the process exit status; skipped or absent tests are visible.

## Out of scope

Waitlists, search, authentication, payments, email, real personal data, public hosting, AI features in the running app, and any reset endpoint exposed publicly.

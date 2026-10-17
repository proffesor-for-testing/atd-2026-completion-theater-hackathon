# API and launcher contract, version 1.1

The fixed request paths and core behavior are in the PRD. Use these response names for the shared verifier, or supply an adapter mapping your field names. A team-owned adapter is part of the frozen source. The auditor should not spend the audit reverse-engineering your schema.

## Local process

The app runs in the foreground, binds to loopback, accepts a configurable port and keeps fixture data in a configurable directory. The optional starter reads `PORT` and `DATA_DIR`. Other stacks can use argv placeholders `{port}` and `{state_dir}` in an adapter. `{python}` resolves to the verifier interpreter on all supported platforms. Supply an explicit reset command which resets **only the newly assigned fixture directory**. Never reset on ordinary restart.

Commands should invoke an installed interpreter, for example `['bash','start.sh']`, `['node','server.js']` or `['{python}','app.py']`. Snapshot transport normalizes file modes, so direct execution of a source script such as `./start.sh` is unsupported. Source IDs identify the documented normalized file content, not arbitrary filesystem metadata.

## Read sessions

GET /sessions returns HTTP 200:

```json
{"sessions":[
  {"id":"CT-101","title":"Catching Ghost Databases","capacity":2,"activeCount":0,"remainingSeats":2},
  {"id":"CT-102","title":"Tests That Can Fail","capacity":3,"activeCount":0,"remainingSeats":3}
]}
```

A bare array is also acceptable with adapter field `sessions: ""`. Session record IDs map through `sessionRecordId`; the `sessionId` mapping is the field in a **reservation**, not in a session record. Counts are JSON integers.

## Reserve and read a reservation

POST /reservations:

```json
{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}
```

Success returns 2xx JSON, for example:

```json
{"id":"generated-stable-id","sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1","status":"active"}
```

GET /reservations/{id} returns that stored record or a 4xx JSON error. The wrapper `{"reservation": {...}}` is acceptable when the adapter sets `reservation: "reservation"`. No wrapper maps through an empty string. A replay returns the same ID and current status. A key conflict returns 4xx with no state change.

## Cancel

POST /reservations/{id}/cancel with `{}` returns the current cancelled record, including on repeat cancellation. Replaying the original create request returns the same cancelled record and must not reactivate it.

## Errors

Return a documented 4xx status with a non-empty JSON `error`. Both of these forms are accepted:

```json
{"error":{"code":"CAPACITY_FULL","message":"No remaining seats"}}
```

```json
{"error":"No remaining seats"}
```

Do not return HTTP 200 with an error. Malformed JSON must reject without changing state and the process must remain available. Count readback alone cannot establish that no hidden/cancelled row was inserted: the verifier labels API results only; inspect the actual store independently for the stronger claim.

## Evidence boundaries

The verifier executes API checks and a real stop/restart. It does not operate the browser or establish UI agreement, reviewer independence, creativity or a final score. Retain its raw receipts plus manual UI/store checks. Ten bounded race batches do not prove race freedom. The command, adapter and source content hash must identify what was tested.

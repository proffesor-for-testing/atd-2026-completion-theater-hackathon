# Session Seat Desk — Team saviauk

Local browser UI and JSON API for two fictional workshops. Use fictional aliases only.

Team/member alias: **saviauk** (solo). Fork: https://github.com/saviauk/atd-2026-completion-theater-hackathon
Branch: **submission/saviauk**. Declared app directory: **starter-python/**, containing all app source, UI, seed data, tests, README and adapter.

## Runtime and installation

Requires **Python 3.11+ with SQLite**, a modern browser, writable disposable fixture storage and an available loopback port. No package install or third-party runtime dependency/lockfile is needed. No AI account, Codex installation, Docker, Node, database server, paid deployment or private service is required. UI assets are local. Build assistants and role guides are not runtime dependencies.

Windows, macOS and Linux are portability targets. Windows/Linux app execution is **NOT RUN** in this build. The observed macOS runtime is Python 3.12.14 / SQLite 3.53.1; no builder-specific executable path is required.

Open a terminal in this app directory, including when extracted from an app-only archive. Verify the exact interpreter; a command called python3 or py -3 can select an older version. Root organizer tools are not needed to run the app.

**macOS/Linux:**

~~~sh
PYTHON=python3
"$PYTHON" -c "import sys,sqlite3; assert sys.version_info >= (3,11), 'Select Python 3.11+'; print(sys.executable); print(sys.version); print('SQLite',sqlite3.sqlite_version)"
~~~

If it fails, set PYTHON to an installed compatible executable, for example python3.12, and rerun the check. Keep the same interpreter for all commands.

**Windows PowerShell:**

~~~powershell
$PythonExe = py -3 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw "Select an installed Python 3.11+ executable." }
& $PythonExe -c "import sys,sqlite3; assert sys.version_info >= (3,11), 'Select Python 3.11+'; print(sys.executable); print(sys.version); print('SQLite',sqlite3.sqlite_version)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ with SQLite is required." }
~~~

If py is unavailable, set $PythonExe to an installed compatible Python executable. The launcher py -3 is executable plus argument, not one quoted executable path.

## Fresh fixture and start

These examples create a new disposable state directory outside source. Save its printed path to resume it later.

**macOS/Linux:**

~~~sh
export PORT=8765
DATA_DIR="$("$PYTHON" -c "import tempfile; print(tempfile.mkdtemp(prefix='session-seat-desk-'))")" || exit $?
export DATA_DIR
"$PYTHON" app.py --reset || exit $?
"$PYTHON" app.py
~~~

**Windows PowerShell:**

~~~powershell
$env:PORT = "8765"
$env:DATA_DIR = & $PythonExe -c "import tempfile; print(tempfile.mkdtemp(prefix='session-seat-desk-'))"
if ($LASTEXITCODE -ne 0) { throw "Fixture directory creation failed." }
& $PythonExe app.py --reset
if ($LASTEXITCODE -ne 0) { throw "Fixture reset failed." }
& $PythonExe app.py
~~~

Open **http://127.0.0.1:8765**. The process stays in the foreground and binds only loopback. If occupied, choose another PORT, such as 8766, and use that URL. Quote paths with spaces.

Fresh reset seeds exactly:

| ID | Title | Capacity | Active | Remaining |
| --- | --- | ---: | ---: | ---: |
| CT-101 | Catching Ghost Databases | 2 | 0 | 2 |
| CT-102 | Tests That Can Fail | 3 | 0 | 3 |

The UI shows actual session counts and provides labelled reserve/lookup/cancel controls, stable request-key retry and visible errors.

## Stop, restart and explicit reset

Stop with **Ctrl+C**. Restart with the same DATA_DIR and PORT **without --reset**: run "$PYTHON" app.py on macOS/Linux or & $PythonExe app.py in PowerShell. Keep the original terminal environment, or restore the saved DATA_DIR path in a new terminal. Normal startup never resets state; an uninitialized directory requires explicit reset first.

To intentionally discard fixture records, stop the server, confirm DATA_DIR is your disposable fixture, then run app.py --reset using the selected interpreter. Reset reseeds sessions and removes that fixture's reservations. It refuses an existing unmarked database or foreign fixture marker. Never bypass this safeguard or use a real database.

Actual store: **DATA_DIR/seats.db**; ownership marker: **DATA_DIR/.fixture-owner**. If DATA_DIR is unset, the default is .state/seats.db under this app. Use external DATA_DIR for verification. There is no HTTP reset endpoint.

## Run the app tests

Run separately from the server; tests create their own isolated child processes and disposable fixtures.

~~~sh
"$PYTHON" -B -m unittest -v test_app
test_status=$?
printf 'Test exit: %s\n' "$test_status"
~~~

~~~powershell
& $PythonExe -B -m unittest -v test_app
$TestExit = $LASTEXITCODE
Write-Output "Test exit: $TestExit"
~~~

Exit 0 means executed tests passed; nonzero means failure/error. Retain stdout/stderr and failure/skip counts. A script wrapping these commands must propagate the captured status using exit "$test_status" or PowerShell exit $TestExit.

The meaningful suite replaces the scaffold sentinel and tests seeds, HTTP/SQLite readback, sequential/concurrent capacity, identical/conflicting-key races, replay/cancellation, invalid inputs, real process restart and guarded reset. Browser usability/UI agreement requires separate execution. Organizer helper CI is not product qualification.

## Independently inspect persisted records

With the same DATA_DIR environment, open the existing store read-only using Python, without a SQLite CLI:

~~~sh
"$PYTHON" -c "import os,pathlib,sqlite3; p=pathlib.Path(os.environ['DATA_DIR'])/'seats.db'; c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True); print('Store:',p); print(c.execute('SELECT * FROM sessions ORDER BY id').fetchall()); print(c.execute('SELECT * FROM reservations ORDER BY id').fetchall()); c.close()"
~~~

In PowerShell pass the same quoted Python code to & $PythonExe -c instead of "$PYTHON" -c. Capture rows/IDs/statuses, stop the actual process, restart without reset, then compare fresh HTTP/UI and independent stored rows. Browser refresh alone is not restart proof.

## API and adapter

JSON names match the published contract exactly. Paths are relative to the loopback URL.

| Method/path | Input | Success | Rejection |
| --- | --- | --- | --- |
| GET /sessions | none | 200: sessions array, id/title/capacity/activeCount/remainingSeats | JSON error if store unavailable |
| POST /reservations | sessionId, attendeeAlias, requestKey | 201 new record; 200 original record on replay | 400 invalid fields/JSON; 404 unknown session; 409 full/key conflict |
| GET /reservations/{id} | saved ID | 200 stored record | 404 unknown ID |
| POST /reservations/{id}/cancel | {} | 200 current cancelled record, including repeat cancellation | 404 unknown ID; 400 invalid JSON |

Example create body:

~~~json
{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}
~~~

Successful record shape:

~~~json
{"id":"generated-stable-id","sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1","status":"active"}
~~~

Aliases are trimmed and otherwise case-sensitive. Keys are global, nonempty strings retained as supplied. Same key/session/trimmed alias returns the original ID/current status, including cancelled. Changed alias/session conflicts without mutation. Cancellation releases one seat once; rebooking needs a new key. Remaining seats equal capacity minus active records.

Errors have nonempty JSON error.code/error.message and non-success HTTP status, never a 200-only error. Oversized JSON is 413; store failure is 503. Invalid JSON, including NaN/Infinity constants, rejects.

adapter.json starts/resets with ["{python}","app.py"] and ["{python}","app.py","--reset"]. The verifier resolves its installed interpreter and supplies isolated PORT/DATA_DIR. Mapping: sessions→sessions, sessionRecordId→id; reservation sessionId→sessionId, reservationId→id, attendeeAlias/requestKey/status directly; reservation has no wrapper. Executable source modes are unnecessary.

## Evidence, known limits and handoff

- Source-bound test/browser/store receipts, failures/skips, requirement matrix and honest PASS/FAIL/NOT RUN manifest are an external sidecar, not runtime dependencies or source-archive contents.
- This README does not award acceptance passes, event points, independent human audit credit or universal race-freedom. See actual receipts. Windows/Linux execution remains NOT RUN.
- Full frozen Git SHA, PR URL, content sourceId and ZIP-byte artifactSha256 are recorded outside source after authorized freeze, avoiding a self-referencing README commit. Working-tree receipts remain preliminary until matching retained source.
- Commit/push/PR, public deployment and external contact require user authorization. Source freeze: **18 November 2026, 21:55 CET**; initial PR/evidence due **22:00 CET**. Postfreeze repairs cannot replace the accepted baseline.

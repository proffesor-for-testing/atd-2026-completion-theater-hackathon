# CLAUDE.md — Team Alt, Completion Theater Hackathon (ATD 2026)

Read this before changing anything. It frames what is being judged, what you may touch,
and the gate a change must pass before anyone calls it done.

## What this repository is

The organizer's participant kit for the **Completion Theater Hackathon** (Agile Testing Days,
18 Nov 2026, 20:15–23:15 CET). Teams build **Session Seat Desk** (`docs/01-Starter-PRD.md`),
freeze an exact commit at **21:55 CET**, open a PR to organizer `main` by **22:00**, then a
different team audits the frozen snapshot. The event exists to catch _completion theater_ —
claims of done that the artifact does not support. Its five patterns are our failure modes too:

| Pattern              | What it looks like from an agent               | What we do instead                                         |
| -------------------- | ---------------------------------------------- | ---------------------------------------------------------- |
| Ghost Database       | "saved" because the response said so           | read the row back, restart the process, read it again      |
| Metric Theater       | "all tests pass" with no fresh output          | quote the runner output, its counts, skips and exit code   |
| Test Theater         | a test that cannot fail                        | break the behaviour in a disposable copy; the test must go red |
| False Positives      | a wrapper that swallows a failure              | exit codes propagate; 4xx means rejection, never 200+error |
| Uncommitted Illusion | "finished" in a working tree nobody received   | verify from the committed SHA / extracted snapshot         |

Judging: app 40 (AC-01..AC-08, 5 each), evidence 30, our audit of another team 20, creativity 10.
Only an **EXECUTED PASS** earns functional points. A clean result means "not observed within these
checks", never "no defects".

## Layout and ownership

| Path                                                   | Owner     | Rule                                                        |
| ------------------------------------------------------ | --------- | ----------------------------------------------------------- |
| `starter-python/`                                      | **us**    | The declared app directory. Everything judged lives here.   |
| `tools/`, `tests/`, `docs/`, `materials/`, `.github/`  | organizer | **Do not edit.** Edits do not change the rules; they muddy the PR. |
| `.claude/skills/score-hackathon`, `.agents/`           | organizer | Facilitator's judging skill. Do not edit or run it as a judge. |
| `team-templates/`                                      | organizer | Copy out of it; do not fill it in place.                    |
| `../team-alt-evidence/` (outside the repo)             | us        | Receipts, verifier reports, screenshots. Never inside the app dir or committed. |

Inside `starter-python/`:

```
app.py              HTTP transport: routing, body limits, security headers, static files
store.py            SQLite store — every rule of the PRD lives here, one transaction per write
sessions.json       Seed data (CT-101 cap 2, CT-102 cap 3) — applied only by --reset
static/             index.html, styles.css, app.js — the pastel UI (no inline script: CSP)
test_app.py         stdlib unittest of store.py — runs with no npm install
tests/api/          Playwright API specs, incl. security.spec.ts (OWASP API baseline)
tests/ui/           Playwright UI specs — full CRUD through the browser, plus axe
tests/support/      Fixture: a fresh app process + fresh DATA_DIR per test
adapter.json        How tools/verify.py starts/resets us and maps our field names
```

## Guardrails (non-negotiable)

1. **Evidence beats memory.** Read the file, run the check. Report every check as PASS / FAIL /
   NOT RUN with its evidence class (REPORTED / STATIC / EXECUTED). Never write PASS for a check
   that did not execute in this session against the current source.
2. **Never weaken a test to make it green** — no deleted assertions, widened selectors,
   `test.skip`, `.only`, raised timeouts to mask a race, or retries. `retries: 0` and
   `forbidOnly` in `playwright.config.ts` stay as they are. Fix the code or report the defect.
3. **A success the API did not confirm is never shown.** The UI renders a reservation only from
   a 2xx response and refreshes counts from `GET /sessions` afterwards.
4. **Reset is explicit and fixture-only.** `app.py` never resets on start. `--reset` refuses an
   unmarked database. Never point `DATA_DIR` at anything but a fresh disposable directory.
5. **Fictional aliases only.** No real names, emails, conference data, credentials or tokens in
   code, fixtures, tests, screenshots or evidence. `.env` files are never read or committed.
6. **Commit and push need the user's explicit yes, every time.** After the 21:55 freeze, nothing
   is pushed to `submission/team-alt` — later repairs go to a separately named branch.
7. **Do not touch organizer files** (see ownership table). Do not add dependencies to the
   runtime app: `app.py`/`store.py` are Python 3.11+ standard library only. Node/Playwright is a
   test-only dependency and lives in `starter-python/package.json` with its lockfile.
8. **Tests are isolated.** Each Playwright test gets its own app process and its own `DATA_DIR`
   (see `tests/support/fixtures.ts`), which is why seat-count assertions are safe here. Never
   share one server between tests that write.
9. **No secrets, no stack traces, no versions** in any HTTP response.

## Quality gate — all must pass before "done"

Run from `starter-python/` unless noted. Quote the real output; do not summarise a run you did
not see.

| # | Gate                         | Command                                                              | Pass means                          |
| - | ---------------------------- | -------------------------------------------------------------------- | ----------------------------------- |
| 1 | Unit (stdlib)                | `py -3 -m unittest -v test_app` (`python3` on macOS/Linux)           | exit 0, no skips                     |
| 2 | Types                        | `npm run typecheck`                                                  | exit 0                               |
| 3 | API + security               | `npx playwright test --project=api`                                  | exit 0, 0 skipped, 0 flaky           |
| 4 | UI CRUD + a11y               | `npx playwright test --project=ui`                                   | exit 0, 0 skipped, 0 flaky           |
| 5 | Shared verifier (repo root)  | `py -3 tools/verify.py --source <extracted snapshot> --adapter <snapshot>/adapter.json --evidence ../team-alt-evidence/verify-<time>` | exit 0, AC02–AC08 PASS |
| 6 | Negative control             | in a **disposable copy**, break one rule in `store.py` (e.g. capacity check) and rerun gate 3 | the matching test FAILS |

Gate 5 runs against an extracted snapshot of a committed SHA (`tools/submission.py snapshot` →
`tools/snapshot.py extract`), not the working tree — that is what an auditor receives. Gates 1–4
can run on the working tree during the build; rerun all of them on the frozen SHA.

What the gate does **not** establish: AC-01 cold start by another team, UI/API agreement judged
by a human, race-freedom beyond the bounded batches, accessibility beyond axe's automated rules.

## Security baseline (OWASP API Top 10, scoped to this PRD)

Each implemented control below has a test: `tests/api/security.spec.ts`, plus XSS rendering in
`tests/ui/crud.spec.ts`. Access control is not implemented and has no test. Keep it that way when
changing `app.py`.

- **Injection (API8/A03):** parameterised SQL only; aliases are stored and returned literally.
- **XSS:** UI writes user data with `textContent`, never `innerHTML`; CSP `script-src 'self'`.
- **Mass assignment (API3):** unknown body fields are rejected; `id`/`status` are server-owned.
- **Resource consumption (API4):** 16 KiB body cap (413), field length caps, 10 s socket timeout.
  No rate limiter — it would break the mandated AC-04 concurrency probe; documented as a gap.
- **CSRF / cross-origin:** POST requires `Content-Type: application/json` (415) and a same-origin
  `Origin` when one is sent (403). No CORS headers are ever emitted.
- **DNS rebinding:** every request must carry `Host: 127.0.0.1:<port>` or `localhost:<port>` (403
  otherwise). Origin==Host alone is not enough: a rebound attacker controls both.
- **Misconfiguration (API8):** CSP, `nosniff`, `frame-ancestors 'none'`/`X-Frame-Options`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on API; `Server` header has no version;
  every error is JSON, including 404/405/501; no stack trace leaves the process.
- **Broken object authorisation (API1/API5, A01): NOT compliant.** The PRD has no users, and
  `GET /reservations` lists every ID, alias and request key to anyone who can reach the port, so
  anyone local can cancel anything. Random UUIDv4 IDs do NOT help while that list exists. Stated
  as a limit, never as a pass.
- Binds `127.0.0.1` only. Static files are an allow-list — no path is joined from the URL.

## Gotchas

- Windows: use `py -3`, not `python` (may be the Store stub). The Playwright fixture resolves the
  real interpreter path so killing it kills the server, not just the `py` launcher.
- `node:sqlite` is used by tests to read the store independently of the API (Ghost Database
  check). It prints an ExperimentalWarning on some Node versions; that is not a failure.
- `tools/verify.py` passes only `PATH`, temp and locale variables plus `PORT`/`DATA_DIR` to the app.
  Do not make the app depend on any other environment variable.

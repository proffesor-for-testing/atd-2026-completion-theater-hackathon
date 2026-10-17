# Completion Theater Hackathon — Agile Testing Days 2026

**Build It, Prove It, Smash It.** A three-hour, hands-on investigation with Dragan Spiridonov and Lalitkumar Bhamare.

18 November 2026, **20:15–23:15 CET**, Room E2+E3, Potsdam. [Published session](https://agiletestingdays.com/2026/session/completion-theater-hackathon-build-it-prove-it-smash-it/).

Build a small app with your chosen AI coding tools, show what really works, then investigate another team's frozen submission. The five patterns are Ghost Database, Metric Theater, Test Theater, False Positives and Uncommitted Illusion. **Rewards are undecided. No product entitlement or sponsorship is promised.**

## Before arriving

1. Download this repository or clone it. No GitHub account or public fork is required to participate.
2. Bring a laptop, charger, a coding agent you can already use, and available model access/credits or a working local model. The event does not supply model subscriptions.
3. Have one familiar local runtime ready. The optional scaffold and helper tools use **Python 3.11+**, standard library only. Check the actual interpreter; some computers have multiple versions.
4. Run `python3 tools/preflight.py`. On Windows, use `py -3 tools/preflight.py`. This checks runtime/SQLite/local ports, not app correctness. If it reports an older Python, select a Python 3.11+ executable explicitly and keep using that same executable for every command.
5. Read the [starter PRD](docs/01-Starter-PRD.md), [API contract](docs/api-contract.md) and [scoring rubric](docs/04-Scoring-Sheets.md), all **rules version 1.1**.

```sh
git clone https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon.git
cd atd-2026-completion-theater-hackathon
python3 tools/preflight.py
```

Use the v1.1.0 release/tag for a stable copy. Read `CHANGELOG.md` for rehearsal fixes. Wi-Fi can fail: download the printable PDFs and your runtime/model dependencies beforehand. There is no package install for the supplied Python tools.

## What is provided

| Material | Where |
| --- | --- |
| Challenge, eight acceptance criteria and API | [PRD](docs/01-Starter-PRD.md), [JSON examples](docs/api-contract.md) |
| Builder verification and peer audit | [Verification](docs/02-Verification-Checklist.md), [Cross-audit](docs/03-Cross-Audit-Checklist.md) |
| 40/30/20/10 rubric and judge forms | [Scoring sheets](docs/04-Scoring-Sheets.md) |
| Exact agenda, facilitation and contingencies | [Facilitator notes](docs/05-Facilitator-Notes.md) |
| Five-pattern reference and receipt form | [Field card](docs/06-Pattern-Reference-Card.md) |
| Editable team handoff files | [Team templates](team-templates/) |
| Optional, deliberately incomplete transport/storage scaffold | [Python starter](starter-python/) |
| Source snapshot, API challenge and score validators | [Helper instructions](tools/README.md) |
| Printable materials and opening/phase deck | [Downloads](materials/) |
| What the technical rehearsal actually established | [Dry-run report](docs/dry-run-report.md) |

The starter is not a finished app. `/health` and the placeholder UI establish only that its server runs. Its test sentinel starts RED deliberately. Implement the product and meaningful tests during the build. Repository CI tests the helper tools, **not** the app your team creates. A green helper check is not a green product check.

## Tonight's flow

| CET | Activity |
| --- | --- |
| 20:15–20:30 | Opening and five patterns |
| 20:30–20:40 | Teams, plan, PRD and rubric |
| 20:40–21:40 | Build, 60 minutes |
| 21:40–22:00 | Verify; freeze source at 21:55; package receipts |
| 22:00–22:05 | Short break and artifact handoff |
| 22:05–22:40 | Independent cross-audit, 35 minutes |
| 22:40–23:00 | Demos and contested findings |
| 23:00–23:10 | Scores and lessons |
| 23:10–23:15 | Close |

Total: 180 minutes. Working app 40 points, evidence 30, **your team's audit of its target** 20, creativity 10. Finding a defect in your app does not award audit points to you. Honest failures can earn evidence credit. A bounded clean audit can earn credit; there is no bounty per bug.

## Sharing and safety

Work in a fresh fixture directory with fictional aliases. Do not use real conference registration, payments, messages, personal data, production services or existing project databases. Share only your inspected source archive and redacted receipts. Do not push participant solutions to this organizer repo. Public hosting is optional and unscored.

The helper launcher is not an OS sandbox. It runs the reviewed command you give it and the app must honor its isolated state directory. Use an isolated OS/container environment for untrusted submissions. Do not grant agents permission to publish, message people or access unrelated workspaces. See [CONTRIBUTING](CONTRIBUTING.md).

## Scope of the rehearsal

One AI-assisted implementation and a separate AI review exercised the original PRD on macOS. That demonstrates a viable familiar-stack path. It does not predict a room of mixed human teams, qualify every language/OS/model setup, or replace a venue rehearsal. The complete rehearsal solution is intentionally excluded from this participant repo.

MIT license for original code and materials in this repository. Agile Testing Days and product names belong to their respective owners; this participant resource does not imply product sponsorship.

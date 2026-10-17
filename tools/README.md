# Optional audit helpers

Python 3.11+ standard library; no package install. Run from the participant repository root. Each script has `--help`. Start with `python3 tools/preflight.py`: it checks Python, SQLite and an ephemeral loopback bind, prints the runtime path, and leaves app acceptance NOT RUN.

## Freeze source

```sh
python3 tools/snapshot.py create starter-python ../team-source.zip
python3 tools/snapshot.py check ../team-source.zip
python3 tools/snapshot.py extract ../team-source.zip ../team-audit-copy
```

Use your app directory instead of `starter-python`. Archives and extracted directories must be new. The archive must be outside the app source. Extraction never merges into an existing directory. No reset/deletion of a database occurs. `sourceId` hashes sorted relative filenames and file content hashes; `artifactSha256` hashes the archive bytes. Both are returned by all three operations. Record both when transferring a ZIP. Extracted source retains `sourceId`; file timestamps do not affect it.

Excluded: `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `evidence`, `runtime`, `data`, `dist`, `build`; `.env*` except `.env.example`; database, SQLite, log, bytecode and journal files. Keep actual source out of these paths. Exclusions are a convenience, **not a secret scanner**: inspect the archive before sharing. Source symlinks are refused. File modes are not preserved: invoke scripts with their interpreter and document any platform setup.

## API challenges

```sh
python3 tools/verify.py --source ../team-audit-copy --adapter tools/adapter.example.json --evidence ../team-audit-evidence
```

The adapter contains argv arrays `start` and `reset`, plus response field mappings. Commands run in the app source directory with `shell=False`. **An installed interpreter/runtime must be argv[0]**: use `["bash", "start.sh"]` or `["{python}", "app.py"]`. Direct source executables such as `./start.sh`, `path/run`, `.\\start.ps1`, or an absolute executable inside the app source are rejected before launch. Bare command names matching a source file are also rejected. Installed absolute runtime paths outside the source remain supported. Snapshot extraction normalizes all files to 0644 and `sourceId` deliberately excludes executable modes; direct executable-launch portability is therefore outside this protocol. Scripts requiring executable bits for their own subprocesses need an interpreter-based adapter or a documented setup step, verified in the cold copy.

`{python}`, `{port}` and `{state_dir}` placeholders are supported. `PORT` and `DATA_DIR` are also environment variables. Children receive only a runtime environment allowlist (`PATH`, Windows system/runtime paths, temporary-directory variables, language/encoding, `HOME`/`USERPROFILE`) plus `PORT`/`DATA_DIR`; inherited API keys, tokens and other private environment variables are not passed. Input JSON fields and API paths follow the PRD. Response mappings accept dotted object paths. `sessions` maps to the session array; `reservation` maps to a reservation object (empty string means the response itself). Session records use `sessionRecordId`; reservation records use `sessionId` and `reservationId` separately.

Each scenario gets a new state directory inside the new evidence directory. Reset is explicit and must honor `DATA_DIR`. AC07 stops and relaunches the actual child process with the same state directory, without reset. All probes target `127.0.0.1`; redirects and proxy environment settings are disabled. Apps must bind loopback and honor `PORT`. This helper is **not an OS sandbox**: review adapter commands and run untrusted submissions in an isolated environment. Apps must run in the foreground; wrapper commands must not daemonize or leave child servers behind.

`report.json` includes API statuses, source hashes before/after, raw HTTP bodies/statuses, process IDs/exits and reset output. Process output is saved beside it. Source changes cause a nonzero exit. Missing behavior, failed commands and failed probes cause a nonzero exit. The supplied incomplete starter is expected to fail most challenges. Test errors are never converted into PASS.

AC04 uses ten separate fresh batches of ten concurrent distinct requests for one remaining seat, plus a sequential full-capacity probe. For quick local iteration only, `--batches 1` reduces this to one batch; the report records that limit. Ten bounded batches are evidence for these trials, not a proof of universal race freedom.

**API PASS is not a complete acceptance criterion or a score.** AC01 is NOT RUN. UI agreement for AC02/03/07, independently reproduced setup/tests, negative-control testing, cross-audit independence and creativity need human execution and evidence. No screenshots are produced. Retained `state-*` directories contain fictional fixture state and are outside the source archive. Do not publish personal data or credentials in evidence.

## Human scoring

Copy `example-score.json` to your evidence directory; enter human decisions and evidence references.

```sh
python3 tools/score.py ../team-audit-evidence/score.json
python3 -m unittest discover -s tests -v
```

All 20 rows are mandatory. Points are integer 0 or 5; 5 requires PASS, an evidence reference, a named adjudicator and `adjudicatorType` (`human` or `ai`, per row or top level). NOT RUN is 0. Declare `mode`: `event` requires human adjudicators and, for C points, a named independent team with `independentAuditTeamType: "human"`; `rehearsal` allows declared AI reviewers/teams and always reports that the score does not qualify a human team or establish independent human audit. Category C requires `independentAuditTeam` and `independentAuditTeamType`. Arithmetic and schema validation cannot prove a declared identity or establish whether evidence is persuasive or independent. A/B/C/D maximums are 40/30/20/10. Creativity and cross-audit points are never inferred from an API result.

The helper tests include an intentionally incomplete server to test failure detection; it is not a reference app. Tests need permission to open a local loopback listener. A restricted environment may deny this; report that environment failure and rerun only where local listeners are permitted.

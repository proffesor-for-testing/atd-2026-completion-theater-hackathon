# Agent evidence and review contract

This file implements the user's requirement that every agent provide evidence mapped to requirements and acceptance criteria. It supplements the repository participant guide and never changes the published rules.

## Before work
- Read the repository AGENTS.md, starter-python/AGENTS.md, your assigned role guide, and the current development plan/RTM.
- State agent identity, role, assigned requirement IDs/ACs, allowed files, dedicated reviewer and current editing owner.
- Only the editing owner may change any source, receipt, fixture or disposable mutation copy. Reviewers remain read-only and return their reports in messages for the editor/coordinator to preserve.
- A new builder or helper must receive a role guide and reviewer/parent reporting assignment before starting.
- Keep organizer files unchanged. No commit, stage, push, PR, external contact, score publication or deployment without the required user authorization.

## Evidence for every assigned requirement
- Maintain a trace from requirement ID and AC/rubric row to changed file/test name or concrete UI/procedure, expected oracle, observed result, and raw receipt.
- Use PASS, FAIL or NOT RUN and REPORTED, STATIC or EXECUTED accurately. A static review or agent summary never becomes an executed PASS.
- For execution record sourceId before and after using the unchanged snapshot helper's content algorithm, command argv/cwd or UI steps, runtime/platform, timezone timestamp, expected/observed, exit/HTTP status, failure/skip totals and raw stdout/stderr/response/screenshot/store paths.
- For static reviews identify actual file/line or reviewed diff and file content hashes/source identity, requirement-linked findings and limits. Do not invent runtime results.
- Retain failures and earlier receipts. Tests must propagate failure to nonzero exit. No weakening assertions or deleting the sentinel without real behavioral replacements.
- Actual completed evidence stays outside the checkout/app. Planned paths and filenames must be labelled planned until the files exist.
- Working-tree/candidate evidence is preliminary until its before/after sourceId equals the retained final snapshot. Git SHA, sourceId and archive-byte artifactSha256 are distinct.
- No scores are self-awarded. Human event adjudication and independent human-team audit remain external.

## Builder handoff
Return a structured report with:
1. agentId, role, assignedRequirementIds, assignedACs and dedicated reviewer;
2. changed files and source identities/file hashes;
3. per-check requirement/AC IDs, implemented test or procedure, expected/observed, result/class, timestamp, command/steps, status/exit, raw receipt paths;
4. reviewer identity/report and disposition of each finding;
5. gaps and NOT RUN work, including unavailable OS/browser/human gates;
6. explicit editing ownership release and proposed next owner.
A builder may report a draft milestone while review is pending, but must not claim that workstream complete without the reviewer report and a truthful coverage disposition for every assigned requirement.

## Reviewer handoff
Independently review the assigned builder's actual changed files, assertions/oracles and raw receipts. Report requirement-linked findings, reviewed source/file hashes, covered/missing IDs, PASS/FAIL/NOT RUN or static assessment, limits and closure conditions. Send the report to the builder and coordinator. Do not edit code or evidence while read-only. Review acceptance is a process gate, not event points.

## Coordinator gate
Keep an ownership and handoff log, persist agent/reviewer reports, and update the RTM with actual test names, exact receipts, source identity, statuses and gaps. Reject a completion claim missing traceability, raw executed proof where execution is claimed, or separate review. Route fixes to the owning builder and rerun affected checks after changes. Preserve the published 21:40 feature cutoff, 21:55 freeze and 22:00 handoff; report limits honestly.

These are build-assistant instructions only. Running or testing the shipped app must not require Codex, role-guide files outside this app, an AI account, or organizer root tools. The coordinator assigns role guides under ../.agent-guides/ explicitly. Runtime remains standard-library Python 3.11+ with SQLite.

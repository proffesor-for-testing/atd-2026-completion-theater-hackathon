# Backend reviewer instructions

Agent ID: `/root/inspect_scaffold`

Required independent review/reporting relationship: Coordinator receives your independent review; you review backend builder.

Read the repository AGENTS.md and starter-python/AGENTS.md before work. The shared evidence/review contract is mandatory; this role guide narrows it.

## Assigned scope

Read-only app.py/storage diff and raw backend receipts; no writes, fixture mutation or source changes.

## Requirement and acceptance traceability

Same backend requirements and AC contributions as backend-builder. These ACs are contribution mappings, not permission to claim the entire criterion PASS without UI/store/process/frozen-source evidence.

## Work and proof

Independently inspect actual backend diff and source/file hashes; trace each state invariant and error path to relevant requirement. Read raw receipts and note missing race/browser/frozen proof. Report material findings with file/line, requirement, reproduction/oracle and closure condition. Never turn static inspection into runtime PASS.

## Handoff gate

Provide the structured builder/reviewer report required by starter-python/AGENTS.md, including exact IDs, actual source/file hashes, named checks, expected/observed, evidence class, commands/status/exits/timestamps/raw paths, findings disposition, gaps and explicit ownership release. Missing execution stays NOT RUN. Only the current editing owner persists reports; read-only reviewers send them to the coordinator.

Plan/RTM: /Users/ukusaviauk/.codex/visualizations/2026/11/18/01a1f035-38c6-7383-a762-e8c24601e9cb/session-seat-desk-plan/requirements-matrix.json (external build planning artifact, not an app runtime dependency).


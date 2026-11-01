# Codespaces and facilitator judging

## Start a Codespace

Use **Code → Codespaces → Create codespace on main** after this configuration is on that branch. To try an unmerged branch, select that branch first. VS Code users can choose **Dev Containers: Reopen in Container** locally with Docker running.

The setup adapts the [HUSTEF masterclass environment](https://github.com/proffesor-for-testing/hustef-2026-memory-masterclass/tree/main/.devcontainer) to this hackathon: Node 24 LTS, Python 3.12/SQLite, GitHub CLI, Claude Code, Codex CLI, Ruflo and Agentic QE. It installs the latest stable npm tags (`@anthropic-ai/claude-code`, `@openai/codex`, `ruflo`, `agentic-qe`) and latest `gh` from GitHub's official apt repository. Native build dependencies are included for npm modules.

There is no automatic project init, swarm, app server, data reset, memory seed, model download, PostgreSQL or Redis service. The supplied Python stack needs no pip dependencies. Runtime verification does not qualify the deliberately incomplete starter or authenticate a model account.

The first setup needs network access and may take several minutes. Failures stop setup with a nonzero exit; fix the reported issue and rerun `bash .devcontainer/post-create.sh`. Installed versions and update time are recorded under `~/.local/state/atd-hackathon/`. A cached/prebuilt image or stopped Codespace is not a promise of today's latest versions. Explicitly refresh before the event:

```sh
bash .devcontainer/update-tools.sh
bash .devcontainer/verify.sh
```

Updates do not run on every restart, so a session is not silently changed mid-build. Rebuild without cache to refresh the base image and runtime Features. Global npm installs use the `node` user's writable `~/.local` prefix; do not use `sudo npm`.

## Authenticate and initialize yourself

Run `claude` and `codex login` interactively, or supply your own provider credentials using Codespaces secrets. Codespaces normally supplies `gh` authentication; inspect it with `gh auth status` and use `gh auth login` if needed. Never put tokens or private `.env` files into the repository. Installed tools do not supply model access or credits.

Choose a separate project directory for each team's build or facilitator experiment. From that directory, inspect current commands and initialize only the integrations you want:

```sh
ruflo init --help
aqe init --help
```

Then use those CLIs' interactive initialization before starting your own swarms. The container does not select a provider, launch a swarm, register MCP servers or grant tools blanket approval for you.

## App ports

The starter binds `127.0.0.1:8765`; use the VS Code **Ports** panel to open its forwarded browser URL. Ports 3000, 5173 and 8000 are also configured for alternative stacks; keep forwarded ports private. The verifier still probes `127.0.0.1` inside the Codespace. A browser URL is not the verifier's API base URL.

Only when you deliberately start an experiment, follow the starter's reset/start commands in `starter-python/README.md`. No app data is created by container setup. The PRD's two fictional sessions are still required in a team's own explicit fresh reset; “no seed data” here describes environment provisioning.

## Score with Claude or Codex

The repository provides the same judging skill to both clients: `.agents/skills/score-hackathon/` is canonical and `.claude/skills/score-hackathon/` routes Claude to it. Reopen the coding-agent session in this repository after adding it. No global skill installation is required.

In Codex: **Use $score-hackathon to assess Team A's frozen archive and evidence in these paths; prepare recommendations for Dragan and Lalit.** In Claude: invoke **/score-hackathon** with the same paths. The skill reads the current published rubric and keeps final event decisions with the named human judges.

Prepare an empty packet (a new output directory; parent must exist):

```sh
python3 .agents/skills/score-hackathon/scripts/judge_packet.py prepare \
  --team 'Team A' --source-id '<verified sourceId or full commit>' \
  --output ../team-a-judging
```

The skill records proposals in `recommendations.md`; `score.json` remains 0/NOT RUN until actual human adjudication. Check approved decisions and combine team files:

```sh
python3 tools/score.py ../team-a-judging/score.json
python3 .agents/skills/score-hackathon/scripts/judge_packet.py scoreboard \
  ../team-a-judging/score.json ../team-b-judging/score.json
```

The scoreboard enforces the existing score schema, refuses rehearsal files and duplicate team names, and applies total, B, C, A tie ordering. It cannot establish whether a claimed human identity or evidence is true. Dragan and Lalit check those. Cross-audit credit belongs to the auditing team, not its target. Rewards remain open.

Run participant submissions only in a separate disposable environment without facilitator secrets, model credentials or unrelated mounts. The facilitator Codespace and verifier command launcher are not sandboxes for arbitrary submitted code. Without safe execution or browser access, leave the affected checks NOT RUN.

## Verification receipt — 1 November 2026

The Dev Containers CLI built this configuration locally on Linux ARM64 (Docker on macOS). A disposable container then ran the actual `post-create.sh` with the repository mounted read-only and no host credentials. All CLI version commands and runtime preflight passed; all 30 helper tests passed inside the container and on the host. Both skill entrypoints passed the skill validator. No project seed state or agent initialization directories were created.

Observed versions: Node 24.22.1, Python 3.12.16, GitHub CLI 2.103.3, Claude Code 2.1.316, Codex 0.166.0, Ruflo 3.68.0 and Agentic QE 3.15.18. These are dated observations, not installation pins. The npm install took about four minutes, including native module compilation. GitHub-hosted Codespaces, model authentication and user-initiated swarms have not been exercised by this check.

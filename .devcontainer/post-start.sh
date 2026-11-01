#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
ATD 2026 · Completion Theater Hackathon
  bash .devcontainer/verify.sh         check installed tools and runtime
  bash .devcontainer/update-tools.sh   explicitly refresh all agent CLIs and gh
  docs/07-Codespaces-and-Judging.md     login, manual init, port forwarding and judging
No app, swarm or model session starts automatically. No fixture or memory data is seeded.
EOF

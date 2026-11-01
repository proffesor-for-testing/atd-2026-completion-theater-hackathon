#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$ROOT/.devcontainer/update-tools.sh"
bash "$ROOT/.devcontainer/verify.sh"
echo 'Ready. Read docs/07-Codespaces-and-Judging.md; initialize your tools in your chosen workspace.'

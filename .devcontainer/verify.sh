#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${NPM_CONFIG_PREFIX:-$HOME/.local}/bin:$PATH"
node -e 'if (Number(process.versions.node.split(".")[0]) < 24) process.exit(1)'
python3 -c 'import sys, sqlite3; assert sys.version_info >= (3, 11); print(sys.version.split()[0], "SQLite", sqlite3.sqlite_version)'

# Some CLI version commands create runtime files. Keep those outside the source tree.
CHECK_DIR="$(mktemp -d)"
trap 'rm -rf "$CHECK_DIR"' EXIT
(
  cd "$CHECK_DIR"
  for tool in node npm gh claude codex ruflo aqe; do
    command -v "$tool" >/dev/null
    echo "Checking $tool"
    "$tool" --version
  done
)
python3 "$ROOT/tools/preflight.py"
echo 'Tool/runtime check passed. App acceptance and model authentication remain NOT RUN.'

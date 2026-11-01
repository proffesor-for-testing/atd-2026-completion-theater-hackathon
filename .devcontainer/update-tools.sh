#!/usr/bin/env bash
# Explicit refresh: latest stable npm tags and the official GitHub CLI apt repository.
set -euo pipefail
export NPM_CONFIG_PREFIX="${NPM_CONFIG_PREFIX:-$HOME/.local}"
export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"
mkdir -p "$NPM_CONFIG_PREFIX/bin" "$HOME/.local/state/atd-hackathon"

node -e 'if (Number(process.versions.node.split(".")[0]) < 24) process.exit(1)'

# The github-cli feature configures cli.github.com/packages when direct download is false.
sudo -n apt-get update
sudo -n apt-get install -y --no-install-recommends gh

# Resolve tags once, install those exact versions, then retain a receipt.
packages=("@anthropic-ai/claude-code" "@openai/codex" "ruflo" "agentic-qe")
specs=()
for package in "${packages[@]}"; do
  version="$(npm view "$package@latest" version)"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Invalid stable version for $package: $version" >&2; exit 1; }
  specs+=("$package@$version")
done
npm install --global --engine-strict --no-fund --no-audit "${specs[@]}"

# Package metadata is recorded without initializing agents, project memory or app data.
npm list --global --depth=0 --json > "$HOME/.local/state/atd-hackathon/npm-versions.json"
gh --version > "$HOME/.local/state/atd-hackathon/gh-version.txt"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$HOME/.local/state/atd-hackathon/updated-at.txt"
echo 'Tools refreshed. Receipt: ~/.local/state/atd-hackathon/'

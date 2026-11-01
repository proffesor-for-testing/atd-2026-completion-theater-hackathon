# Node 24 LTS also supports the current AQE Node >=22.13 requirement.
FROM mcr.microsoft.com/devcontainers/typescript-node:24-bookworm

USER root
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential pkg-config libsqlite3-dev sqlite3 curl ca-certificates \
      jq ripgrep tmux less \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Agent installs remain writable by the remote user; no root-owned project memory.
RUN mkdir -p /home/node/.local/bin /home/node/.local/state/atd-hackathon \
 && chown -R node:node /home/node/.local
ENV NPM_CONFIG_PREFIX=/home/node/.local
ENV PATH=/home/node/.local/bin:${PATH}
USER node

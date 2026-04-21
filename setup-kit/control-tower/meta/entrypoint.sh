#!/bin/bash
set -e

mkdir -p /data/meta/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/meta/.openspace /app/.openspace
fi

# Refresh host_skills
if [ -d /repo/host_skills ]; then
    cp -rn /repo/host_skills /app/host_skills || true
fi

exec python -u agent.py

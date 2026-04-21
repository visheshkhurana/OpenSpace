#!/bin/bash
set -e

# Ensure .openspace SQLite dir is available
mkdir -p /data/api/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/api/.openspace /app/.openspace
fi

# Refresh host_skills from repo root if symlink not set
if [ ! -d /app/host_skills ] && [ -d /repo/host_skills ]; then
    ln -sfn /repo/host_skills /app/host_skills
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2

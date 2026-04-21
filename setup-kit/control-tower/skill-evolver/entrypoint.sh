#!/bin/bash
set -e
mkdir -p /data/skill-evolver/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/skill-evolver/.openspace /app/.openspace
fi
if [ -d /repo/host_skills ]; then
    cp -rn /repo/host_skills /app/host_skills || true
fi
exec python -u runner.py

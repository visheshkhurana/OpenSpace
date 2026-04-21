#!/bin/bash
set -e

mkdir -p /data/worker/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/worker/.openspace /app/.openspace
fi

if [ -d /repo/host_skills ]; then
    cp -rn /repo/host_skills /app/host_skills || true
fi

exec python -u worker.py

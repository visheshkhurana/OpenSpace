#!/bin/bash
set -e
mkdir -p /data/tournament/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/tournament/.openspace /app/.openspace
fi
exec python -u runner.py

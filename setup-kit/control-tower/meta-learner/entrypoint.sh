#!/bin/bash
set -e
mkdir -p /data/meta-learner/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/meta-learner/.openspace /app/.openspace
fi
exec python -u runner.py

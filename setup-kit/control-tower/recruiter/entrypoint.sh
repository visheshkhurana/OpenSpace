#!/bin/bash
set -e
mkdir -p /data/recruiter/.openspace
if [ ! -L /app/.openspace ]; then
    ln -sfn /data/recruiter/.openspace /app/.openspace
fi
exec python -u runner.py

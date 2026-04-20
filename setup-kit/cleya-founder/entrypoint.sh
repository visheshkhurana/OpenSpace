#!/usr/bin/env bash
# Cleya founder agent entrypoint
set -e

# OpenSpace SkillStore hardcodes db at <repo>/.openspace/openspace.db.
# Symlink to persistent disk so skills + analyses persist across deploys.
DISK_SKILL_DIR=/data/openspace/.openspace
mkdir -p "$DISK_SKILL_DIR"
rm -rf /opt/openspace-src/.openspace
ln -s "$DISK_SKILL_DIR" /opt/openspace-src/.openspace

# Seed host skills (refresh from image so SKILL.md edits ship cleanly)
mkdir -p /data/openspace/host_skills
# 1) OpenSpace built-ins
for sk in delegate-task skill-discovery; do
  if [ ! -d "/data/openspace/host_skills/$sk" ] && [ -d "/opt/openspace-src/openspace/host_skills/$sk" ]; then
    cp -r "/opt/openspace-src/openspace/host_skills/$sk" /data/openspace/host_skills/
    echo "[entrypoint] seeded host skill: $sk"
  fi
done
# 2) Cleya-specific skills (always refresh)
if [ -d /opt/agent/host_skills ]; then
  for sk in /opt/agent/host_skills/*/; do
    name=$(basename "$sk")
    rm -rf "/data/openspace/host_skills/$name"
    cp -r "$sk" /data/openspace/host_skills/
    echo "[entrypoint] refreshed skill: $name"
  done
fi

mkdir -p /data/cleya
echo "[entrypoint] starting Cleya founder agent (interval=${CYCLE_INTERVAL_HOURS:-3}h)"
exec python -u /opt/agent/app/agent.py

#!/usr/bin/env bash
# 1. Restore skill DB from Supabase (if a snapshot exists)
# 2. Start litestream replication in background
# 3. Run the bot
set -e

# OpenSpace's SkillStore hardcodes db at <repo>/.openspace/openspace.db.
# Symlink that to our persistent disk so it survives redeploys AND gets
# replicated to Supabase by litestream.
DISK_SKILL_DIR=/data/openspace/.openspace
mkdir -p "$DISK_SKILL_DIR"
rm -rf /opt/openspace-src/.openspace
ln -s "$DISK_SKILL_DIR" /opt/openspace-src/.openspace
DB="$DISK_SKILL_DIR/openspace.db"

# Mounted disk overlays /data at runtime, so seed host_skills here (idempotent)
mkdir -p /data/openspace/host_skills
# 1) OpenSpace built-in skills
for sk in delegate-task skill-discovery; do
  if [ ! -d "/data/openspace/host_skills/$sk" ] && [ -d "/opt/openspace-src/openspace/host_skills/$sk" ]; then
    cp -r "/opt/openspace-src/openspace/host_skills/$sk" /data/openspace/host_skills/
    echo "[entrypoint] seeded host skill: $sk"
  fi
done
# 2) Bot-specific skills (always refresh from image so SKILL.md edits take effect on redeploy)
if [ -d /opt/bot/host_skills ]; then
  for sk in /opt/bot/host_skills/*/; do
    name=$(basename "$sk")
    rm -rf "/data/openspace/host_skills/$name"
    cp -r "$sk" /data/openspace/host_skills/
    echo "[entrypoint] refreshed bot skill: $name"
  done
fi

echo "[entrypoint] restoring skill DB from Supabase if a snapshot exists..."
litestream restore -if-replica-exists -config /etc/litestream.yml "$DB" || \
  echo "[entrypoint] no snapshot yet — starting fresh"

echo "[entrypoint] starting litestream replication in background"
litestream replicate -config /etc/litestream.yml &
LTS_PID=$!

# Forward signals so docker stop terminates cleanly
trap "kill -TERM $LTS_PID 2>/dev/null; exit" TERM INT

echo "[entrypoint] starting bot"
exec python /opt/bot/app/main.py

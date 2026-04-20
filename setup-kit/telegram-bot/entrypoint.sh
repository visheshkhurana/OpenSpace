#!/usr/bin/env bash
# 1. Restore skill DB from Supabase (if a snapshot exists)
# 2. Start litestream replication in background
# 3. Run the bot
set -e

DB="${OPENSPACE_DB_PATH:-/data/openspace/.openspace/openspace.db}"
mkdir -p "$(dirname "$DB")"

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

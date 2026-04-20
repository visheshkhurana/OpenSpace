#!/usr/bin/env bash
# Install Litestream + wire it to Supabase for OpenSpace skill DB sync.
# Run this on EACH device you want to share evolution between.
set -euo pipefail

c_blue() { printf "\033[34m%s\033[0m\n" "$*"; }
c_green(){ printf "\033[32m%s\033[0m\n" "$*"; }
ask()    { local var="$1" prompt="$2"; read -r -p "$prompt" v; printf -v "$var" '%s' "$v"; }
ask_secret() { local var="$1" prompt="$2"; read -r -s -p "$prompt" v; echo; printf -v "$var" '%s' "$v"; }

OS="$(uname -s)"
DEVICE_ID="$(hostname -s 2>/dev/null || hostname)"
OPENSPACE_DB_PATH="${OPENSPACE_DB_PATH:-$HOME/OpenSpace/.openspace/openspace.db}"
KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Install litestream binary
c_blue "==> 1/5 Installing litestream"
if command -v litestream >/dev/null 2>&1; then
  c_green "    already installed: $(litestream version)"
else
  case "$OS" in
    Darwin) brew install benbjohnson/litestream/litestream ;;
    Linux)
      curl -fsSL https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.deb -o /tmp/lts.deb
      sudo dpkg -i /tmp/lts.deb || (sudo apt-get update && sudo apt-get -f install -y && sudo dpkg -i /tmp/lts.deb)
      ;;
    *) echo "Unsupported OS: $OS — install litestream manually from https://litestream.io"; exit 1 ;;
  esac
fi

# 2. Collect Supabase S3 credentials
c_blue "==> 2/5 Supabase S3 credentials"
echo "    Get these from Supabase dashboard → openspace-sync → Storage → S3 Connection."
echo "    Project Ref is also visible in the URL of the dashboard."
ask        SUPABASE_PROJECT_REF "    Project ref (e.g. fhrynagbidbznfvuoxcn): "
ask        SUPABASE_S3_REGION   "    Region [ap-south-1]: "
SUPABASE_S3_REGION="${SUPABASE_S3_REGION:-ap-south-1}"
ask        SUPABASE_S3_KEY_ID   "    S3 access key ID: "
ask_secret SUPABASE_S3_SECRET   "    S3 secret access key: "

# 3. Write env file litestream will read
c_blue "==> 3/5 Writing litestream env"
ENV_DIR="$HOME/.openspace"
mkdir -p "$ENV_DIR"
cat > "$ENV_DIR/litestream.env" <<EOF
SUPABASE_PROJECT_REF=$SUPABASE_PROJECT_REF
SUPABASE_S3_REGION=$SUPABASE_S3_REGION
SUPABASE_S3_KEY_ID=$SUPABASE_S3_KEY_ID
SUPABASE_S3_SECRET=$SUPABASE_S3_SECRET
OPENSPACE_DB_PATH=$OPENSPACE_DB_PATH
DEVICE_ID=$DEVICE_ID
EOF
chmod 600 "$ENV_DIR/litestream.env"
cp "$KIT_DIR/litestream/litestream.yml" "$ENV_DIR/litestream.yml"
c_green "    wrote $ENV_DIR/litestream.env (mode 600) and litestream.yml"

# 4. First-boot restore (pulls latest snapshot if one exists from another device)
c_blue "==> 4/5 First-boot restore (no-op on a fresh device)"
mkdir -p "$(dirname "$OPENSPACE_DB_PATH")"
set -a; . "$ENV_DIR/litestream.env"; set +a
if [ ! -f "$OPENSPACE_DB_PATH" ]; then
  litestream restore -if-replica-exists -config "$ENV_DIR/litestream.yml" "$OPENSPACE_DB_PATH" || \
    c_green "    no remote snapshot yet — fresh DB will be created on first openspace run"
else
  c_green "    local DB already exists, leaving it (litestream will replicate from here)"
fi

# 5. Install service to run litestream continuously
c_blue "==> 5/5 Installing background service"
case "$OS" in
  Darwin)
    PLIST="$HOME/Library/LaunchAgents/cloud.openspace.litestream.plist"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>cloud.openspace.litestream</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string><string>-c</string>
    <string>set -a; . $ENV_DIR/litestream.env; set +a; exec litestream replicate -config $ENV_DIR/litestream.yml</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$ENV_DIR/litestream.log</string>
  <key>StandardErrorPath</key><string>$ENV_DIR/litestream.log</string>
</dict></plist>
EOF
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load   "$PLIST"
    c_green "    launchd agent loaded: $PLIST"
    ;;
  Linux)
    UNIT="$HOME/.config/systemd/user/openspace-litestream.service"
    mkdir -p "$(dirname "$UNIT")"
    cat > "$UNIT" <<EOF
[Unit]
Description=OpenSpace skill DB → Supabase replication
After=network-online.target

[Service]
Type=simple
EnvironmentFile=$ENV_DIR/litestream.env
ExecStart=/usr/bin/litestream replicate -config $ENV_DIR/litestream.yml
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now openspace-litestream.service
    c_green "    systemd user service started: openspace-litestream"
    ;;
esac

cat <<EOF

$(c_green "================================================================")
$(c_green "  OpenSpace skill DB is now syncing to Supabase.")
$(c_green "================================================================")

  Local DB:     $OPENSPACE_DB_PATH
  Replica:      s3://openspace-db/skills/$DEVICE_ID @ Supabase project $SUPABASE_PROJECT_REF
  Logs:         $ENV_DIR/litestream.log  (macOS) or  journalctl --user -u openspace-litestream  (Linux)

  Verify:
    litestream snapshots -config ~/.openspace/litestream.yml $OPENSPACE_DB_PATH

  On a new device, just re-run this script — it will restore from
  the replica, then start streaming changes back.

EOF

#!/usr/bin/env bash
# Apply OpenSpace MCP config to all four agents on your machine.
# Safe: backs up existing configs to *.bak before writing.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

backup_and_write() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ]; then
    cp "$dst" "$dst.bak.$(date +%s)"
    echo "   backed up existing $dst"
  fi
  cp "$src" "$dst"
  echo "   wrote $dst"
}

echo "==> Claude Code"
backup_and_write "$KIT_DIR/configs/claude_code_mcp.json" "$HOME/.claude/mcp.json"

echo "==> Cursor"
backup_and_write "$KIT_DIR/configs/cursor_mcp.json" "$HOME/.cursor/mcp.json"

echo "==> Codex"
# Codex uses TOML; we APPEND, never overwrite, since users usually have other servers.
CODEX_CFG="$HOME/.codex/config.toml"
mkdir -p "$(dirname "$CODEX_CFG")"
touch "$CODEX_CFG"
if ! grep -q "mcp_servers.openspace" "$CODEX_CFG" 2>/dev/null; then
  cp "$CODEX_CFG" "$CODEX_CFG.bak.$(date +%s)"
  echo "" >> "$CODEX_CFG"
  cat "$KIT_DIR/configs/codex_mcp.toml" >> "$CODEX_CFG"
  echo "   appended openspace block to $CODEX_CFG"
else
  echo "   openspace already present in $CODEX_CFG — skipped"
fi

echo "==> OpenClaw / nanobot"
# Both read ~/.config/<host>/mcp.json by default. Adjust if yours differs.
for host in openclaw nanobot; do
  backup_and_write "$KIT_DIR/configs/openclaw_nanobot_mcp.json" "$HOME/.config/$host/mcp.json"
done

echo ""
echo "=============================================================="
echo " All 4 agents now share:"
echo "   Skills:    ~/.openspace/host_skills"
echo "   Workspace: ~/OpenSpace (single SQLite skill DB)"
echo " Restart each agent to pick up the new MCP server."
echo "=============================================================="

#!/usr/bin/env bash
# OpenSpace one-shot bootstrap.
# Run this on your laptop. Does everything end-to-end:
#   1. Clones your fork
#   2. Installs openspace + openspace-mcp
#   3. Prompts for API keys, writes .env
#   4. Wires Claude Code, Codex, Cursor, OpenClaw, nanobot
#   5. Smoke-tests the install
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/visheshkhurana/OpenSpace/setup-kit/setup-kit/scripts/bootstrap.sh | bash
# OR
#   bash setup-kit/scripts/bootstrap.sh

set -euo pipefail

KIT_REPO="https://github.com/visheshkhurana/OpenSpace.git"
KIT_BRANCH="setup-kit"
KIT_DIR="${OPENSPACE_KIT_DIR:-$HOME/OpenSpace-kit}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"

c_green() { printf "\033[32m%s\033[0m\n" "$*"; }
c_blue()  { printf "\033[34m%s\033[0m\n" "$*"; }
c_red()   { printf "\033[31m%s\033[0m\n" "$*"; }
ask()     { local var="$1" prompt="$2"; read -r -p "$prompt" v; printf -v "$var" '%s' "$v"; }

c_blue "==> Step 1/5: fetching the kit"
if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/install_local.sh" ]; then
  if [ ! -d "$KIT_DIR" ]; then
    git clone -b "$KIT_BRANCH" --depth 1 "$KIT_REPO" "$KIT_DIR"
  else
    git -C "$KIT_DIR" pull --rebase
  fi
  SCRIPT_DIR="$KIT_DIR/setup-kit/scripts"
fi
cd "$SCRIPT_DIR/.."

c_blue "==> Step 2/5: installing OpenSpace"
bash "$SCRIPT_DIR/install_local.sh"

c_blue "==> Step 3/5: API keys"
ENV_FILE="$HOME/OpenSpace/openspace/.env"
if grep -q "REPLACE_ME" "$ENV_FILE" 2>/dev/null; then
  echo ""
  echo "  Press Enter to skip a key (you can paste it later in $ENV_FILE)."
  ask OPENAI_KEY     "  OPENAI_API_KEY (sk-...): "
  ask OPENSPACE_KEY  "  OPENSPACE_API_KEY (os-... from open-space.cloud, optional): "

  cp "$(dirname "$SCRIPT_DIR")/configs/env.template" "$ENV_FILE"
  [ -n "${OPENAI_KEY:-}" ]    && sed -i.bak "s|sk-REPLACE_ME|$OPENAI_KEY|"     "$ENV_FILE"
  [ -n "${OPENSPACE_KEY:-}" ] && sed -i.bak "s|os-REPLACE_ME|$OPENSPACE_KEY|" "$ENV_FILE"
  rm -f "$ENV_FILE.bak"
  c_green "    .env written to $ENV_FILE"
else
  c_green "    .env already populated, skipping"
fi

c_blue "==> Step 4/5: wiring agents (Claude Code, Codex, Cursor, OpenClaw, nanobot)"
bash "$SCRIPT_DIR/apply_configs.sh"

c_blue "==> Step 5/5: smoke test"
# shellcheck disable=SC1091
source "$HOME/OpenSpace/.venv/bin/activate"
python -c "import openspace; print('   openspace package OK, version:', getattr(openspace, '__version__', 'dev'))"
openspace-mcp --help >/dev/null && c_green "   openspace-mcp OK"

cat <<EOF

$(c_green "================================================================")
$(c_green "  DONE. OpenSpace is now active for ALL your agents.")
$(c_green "================================================================")

  What just happened:
    • Repo:   $HOME/OpenSpace
    • Skills: $HOME/.openspace/host_skills (single source of truth)
    • Agents wired: Claude Code, Codex, Cursor, OpenClaw, nanobot
    • All 5 share ONE skill DB at $HOME/OpenSpace/.openspace/openspace.db

  NEXT STEPS (manual):
    1. Restart each agent (Claude Code, Cursor, etc.) — they pick up MCP on launch.
    2. Try a task in any agent. Ask it to:
         "use the openspace skill discovery tool to list available skills"
       to confirm the connection.
    3. Watch skills evolve over your normal usage. The savings compound.

  CLOUD LATER:
    When ready to add a shared cloud DB across devices, see
    $HOME/OpenSpace-kit/setup-kit/railway/DEPLOY.md
    (or swap to DigitalOcean / Supabase Postgres — same shape).

EOF

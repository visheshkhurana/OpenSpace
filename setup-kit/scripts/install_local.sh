#!/usr/bin/env bash
# OpenSpace local install — run on your laptop / dev machine
# Requires: Python 3.12+, git, Node.js >= 20 (for dashboard only)
set -euo pipefail

INSTALL_DIR="${OPENSPACE_HOME:-$HOME/OpenSpace}"
FORK_URL="https://github.com/visheshkhurana/OpenSpace.git"

echo "==> Installing OpenSpace at: $INSTALL_DIR"

# 1. Sparse clone (skips ~50 MB assets folder — big speedup)
if [ ! -d "$INSTALL_DIR" ]; then
  # Full clone is simpler and reliable across git versions.
  # The assets/ dir is ~50 MB — acceptable one-time cost.
  git clone --depth 1 "$FORK_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
else
  echo "==> Directory exists, pulling latest"
  cd "$INSTALL_DIR"
  git pull --rebase
fi

# 2. Virtualenv (keeps OpenSpace isolated from system Python)
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. Install OpenSpace in editable mode
pip install --upgrade pip
pip install -e .

# 4. Verify
openspace-mcp --help >/dev/null && echo "==> openspace-mcp OK"
openspace --help   >/dev/null && echo "==> openspace CLI OK"

# 5. Seed env file if missing
if [ ! -f "openspace/.env" ]; then
  cp openspace/.env.example openspace/.env 2>/dev/null || true
  echo "==> Created openspace/.env — edit it with your keys (see configs/env.template)"
fi

# 6. Shared skills directory used by ALL your agents (single source of truth)
SHARED_SKILLS="$HOME/.openspace/host_skills"
mkdir -p "$SHARED_SKILLS"
cp -rn "$INSTALL_DIR/openspace/host_skills/delegate-task"    "$SHARED_SKILLS/" || true
cp -rn "$INSTALL_DIR/openspace/host_skills/skill-discovery"  "$SHARED_SKILLS/" || true

echo ""
echo "=============================================================="
echo " OpenSpace installed."
echo "   Repo:        $INSTALL_DIR"
echo "   Shared skills: $SHARED_SKILLS"
echo "   Next: fill in keys in $INSTALL_DIR/openspace/.env"
echo "   Then apply the MCP configs from ./configs/"
echo "=============================================================="

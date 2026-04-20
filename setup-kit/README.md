# OpenSpace Universal Setup Kit

Goal: **Every agent you use — Claude Code, Codex, Cursor, OpenClaw, nanobot — plugs into one
self-evolving skill layer so token cost drops across all of them regardless of the LLM.**

Built for your fork: [visheshkhurana/OpenSpace](https://github.com/visheshkhurana/OpenSpace).

---

## What this kit does

- **Path A** — wires OpenSpace into all 4 agents via MCP. One shared skills dir, one shared
  SQLite skill DB. When Claude Code learns a pattern, Cursor and Codex inherit it
  immediately.
- **Path B** — sets up the standalone `openspace` CLI with OpenAI GPT as the default
  backbone (per your pick).
- **Cloud community** — OPENSPACE_API_KEY wired everywhere, so your evolution also syncs to
  `open-space.cloud` and pulls community skills back.
- **Railway deploy** — optional shared cloud endpoint so every device hits one DB.

---

## Install sequence (on your laptop)

```bash
# 1. Unzip the kit somewhere, then:
cd openspace-kit
chmod +x scripts/*.sh

# 2. Clone + install OpenSpace
./scripts/install_local.sh
#    → installs at ~/OpenSpace (sparse, no assets), creates ~/.openspace/host_skills
#    → takes ~2-3 min; pulls deps like litellm, mcp, sqlalchemy

# 3. Put your keys in place
cp configs/env.template ~/OpenSpace/openspace/.env
$EDITOR ~/OpenSpace/openspace/.env
#    → add OPENAI_API_KEY and OPENSPACE_API_KEY

# 4. Apply MCP configs to all 4 agents
./scripts/apply_configs.sh

# 5. Restart each agent. Done.
```

Verify with:

```bash
source ~/OpenSpace/.venv/bin/activate
openspace --query "list the skills currently registered"
```

---

## Deploy Railway shared DB (optional but recommended)

See [`railway/DEPLOY.md`](railway/DEPLOY.md). After deploying, switch the agents from the
stdio config to `configs/remote_mcp_template.json` and every device shares one DB.

---

## Why this saves tokens

| Mechanism | How it cuts cost |
|---|---|
| Skill reuse | Successful workflows are replayed as skills instead of re-reasoned. Measured **−46% tokens** on GDPVal. |
| FIX evolution | Broken skills self-heal. No more wasted tokens on retries. |
| CAPTURED patterns | Novel wins become reusable skills automatically. |
| Cross-agent sharing | Claude Code evolves a skill → Codex uses it on the next call. No relearning. |
| Cloud community | Skills others already evolved are importable — skip the learning cost entirely. |

LLM-agnostic: swap `OPENSPACE_MODEL` between OpenAI, Anthropic, Qwen, whatever. Savings
persist because skills are stored as plain markdown, not model-specific weights.

---

## File map

```
openspace-kit/
├── README.md                           (this file)
├── scripts/
│   ├── install_local.sh                clone + sparse checkout + venv + pip install
│   └── apply_configs.sh                writes MCP config to all 4 agents (with backups)
├── configs/
│   ├── env.template                    OPENAI_API_KEY + OPENSPACE_API_KEY template
│   ├── claude_code_mcp.json            → ~/.claude/mcp.json
│   ├── codex_mcp.toml                  → appended to ~/.codex/config.toml
│   ├── cursor_mcp.json                 → ~/.cursor/mcp.json
│   ├── openclaw_nanobot_mcp.json       → ~/.config/{openclaw,nanobot}/mcp.json
│   └── remote_mcp_template.json        swap-in once Railway is live
└── railway/
    ├── Dockerfile                      streamable-HTTP openspace-mcp
    ├── railway.json                    Railway service config
    └── DEPLOY.md                       step-by-step
```

---

## Switching the backbone LLM later

Nothing locks you to OpenAI. To switch any agent on the fly:

```bash
# Set per-call:
openspace --model "anthropic/claude-sonnet-4-5" --query "..."

# Or change default in ~/OpenSpace/openspace/.env:
OPENSPACE_MODEL=openrouter/qwen/qwen3.5-plus   # the paper's cheap/best config
```

Skills keep evolving either way — that's the point.

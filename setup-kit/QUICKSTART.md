# OpenSpace Quickstart — Local

**One command on your laptop. ~3 minutes.**

```bash
curl -fsSL https://raw.githubusercontent.com/visheshkhurana/OpenSpace/setup-kit/setup-kit/scripts/bootstrap.sh | bash
```

That's it. The script:

1. Clones your fork to `~/OpenSpace`
2. `pip install -e .` inside a venv
3. Prompts for `OPENAI_API_KEY` (and optional `OPENSPACE_API_KEY` for community sync)
4. Writes MCP configs to all 5 agents (Claude Code, Codex, Cursor, OpenClaw, nanobot)
5. Smoke-tests the install

Then restart each agent.

## Verify it worked

In any agent (try Claude Code first):

```
use the openspace skill_discovery tool to list available skills
```

If it lists `delegate-task` and `skill-discovery`, you're live.

## What you get

| Mechanism | Token savings |
|---|---|
| Skill reuse across agents | ~46% on repeat task patterns |
| FIX evolution (auto-repair) | eliminates retry loops |
| Cross-agent sharing | learnings in Claude Code instantly available in Cursor / Codex |

LLM-agnostic — switch backbones any time via `OPENSPACE_MODEL` in `.env`.

## Cloud later

When you want one shared skill DB across multiple machines, options ranked by effort:

1. **Cheapest** — Supabase Postgres backend (you already have a Supabase connector)
2. **Easiest** — DigitalOcean App Platform (~$5/mo)
3. **Original plan** — Railway (needs working token)

All three use the same Dockerfile in `setup-kit/railway/`.

## Troubleshooting

- **`openspace-mcp: command not found`** — the venv isn't active. Run `source ~/OpenSpace/.venv/bin/activate` first, or update your shell rc.
- **Agent doesn't see openspace tools** — restart the agent fully (quit, not just close window). MCP servers are loaded at startup.
- **Bootstrap script fails on git clone** — check `git --version` is ≥ 2.25.

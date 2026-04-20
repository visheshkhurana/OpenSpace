# Deploy OpenSpace MCP to Railway (shared cloud DB)

This gives every agent on every device a **single shared skill database** via
streamable HTTP. Local `.openspace/openspace.db` syncs up to this one.

## 1. Create the service

```bash
# from /openspace-kit/railway
railway login
railway init           # name it e.g. openspace-mcp
railway up             # builds the Dockerfile and deploys
```

Or connect the GitHub fork directly in the Railway UI and point it at
`/openspace-kit/railway/Dockerfile`.

## 2. Add a persistent volume

Railway UI → Service → Volumes → **New Volume**
- Mount path: `/workspace`
- Size: 1 GB is plenty (the skill DB is tiny; recordings are the only growth vector).

Without this, your evolved skills wipe on every redeploy.

## 3. Set variables

In Railway → Variables:

| Var | Value |
|---|---|
| `OPENAI_API_KEY`      | your OpenAI key (for LLM calls from the server) |
| `OPENSPACE_API_KEY`   | your open-space.cloud key |
| `OPENSPACE_MODEL`     | `openai/gpt-4.1` (or `openai/gpt-4o` to save further) |
| `PORT`                | (auto-set by Railway — leave alone) |

## 4. Wire your agents to the remote server

Once deployed, Railway gives you a URL like
`https://openspace-mcp-production.up.railway.app`.

Use `/openspace-kit/configs/remote_mcp_template.json` — replace the URL placeholder
and apply to each agent (Claude Code / Cursor / Codex / OpenClaw / nanobot).

## 5. Verify

```bash
curl https://<your-app>.up.railway.app/healthz
# → {"status":"ok"}
```

Then kick off any task from any agent — watch the Railway logs to see evolution
events stream in. The same SQLite DB is now shared across all of them.

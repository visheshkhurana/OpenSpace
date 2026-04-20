---
name: render-ops
description: Manage Render.com services from Telegram — list services, tail logs, trigger redeploys, check deploy status. Use when the user says "render status", "render logs <name>", "render redeploy <name>", "is the bot up", "redeploy".
---

# Render Ops

The Render API key is available in the container env as `RENDER_API_KEY`
(set it once via Render dashboard if missing — see "Setup" below).

The owner ID for this account is `tea-d6ueienfte5s738bncj0`.

## List services

User: `render status`, `render list`, `what services do I have`

```bash
curl -s -H "Authorization: Bearer ${RENDER_API_KEY}" \
  "https://api.render.com/v1/services?limit=20" \
 | python3 -c '
import sys,json
for r in json.load(sys.stdin):
    s=r["service"]
    print(f"{s[\"name\"]:30s}  {s[\"type\"]:18s}  {s.get(\"branch\",\"-\"):10s}  suspended={s.get(\"suspended\",\"\")}")
'
```

## Latest deploy status

User: `render status <name>`, `is <name> live`

```bash
# resolve service id by name
SVC_ID=$(curl -s -H "Authorization: Bearer ${RENDER_API_KEY}" \
  "https://api.render.com/v1/services?name=${NAME}&limit=1" \
 | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d[0]["service"]["id"] if d else "")')

curl -s -H "Authorization: Bearer ${RENDER_API_KEY}" \
  "https://api.render.com/v1/services/${SVC_ID}/deploys?limit=1" \
 | python3 -c '
import sys,json
d=json.load(sys.stdin)[0]["deploy"]
print(f"status: {d[\"status\"]}")
print(f"commit: {d[\"commit\"][\"id\"][:7]} — {d[\"commit\"][\"message\"].splitlines()[0]}")
print(f"finishedAt: {d.get(\"finishedAt\")}")
'
```

## Tail logs

User: `render logs <name>`, `tail <name>`

```bash
SVC_ID=...   # resolve as above
START=$(python3 -c "from datetime import datetime,timedelta,timezone;print((datetime.now(timezone.utc)-timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
END=$(python3 -c "from datetime import datetime,timezone;print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))")
curl -s -H "Authorization: Bearer ${RENDER_API_KEY}" \
  "https://api.render.com/v1/logs?ownerId=tea-d6ueienfte5s738bncj0&resource=${SVC_ID}&type=app&limit=30&startTime=${START}&endTime=${END}" \
 | python3 -c '
import sys,json
d=json.load(sys.stdin)
for l in d.get("logs",[]):
    print(l.get("timestamp","")[:19], l.get("message","")[:200])
'
```

## Trigger redeploy

User: `render redeploy <name>`, `redeploy <name>`

```bash
SVC_ID=...   # resolve as above
curl -s -X POST -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"clearCache":"do_not_clear"}' \
  "https://api.render.com/v1/services/${SVC_ID}/deploys" \
 | python3 -c 'import sys,json;d=json.load(sys.stdin);print(f"triggered: {d.get(\"id\")} status={d.get(\"status\")}")'
```

## Setup (only if RENDER_API_KEY missing)

If `${RENDER_API_KEY}` is empty, tell the user:
> Set RENDER_API_KEY in Render dashboard → openspace-telegram-bot → Environment.
> Get a key at https://dashboard.render.com/u/settings#api-keys

## Tips

- Always reply with concise output — one block of text, suitable for Telegram.
- Never expose the API key in replies.
- If a service name is ambiguous, list all matching ones.
- For long log output, return only the last ~20 lines.

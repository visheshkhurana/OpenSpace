# Cleya Control Tower — Handover Document

**Status:** LIVE in production (Render, Singapore region)
**Repo:** https://github.com/visheshkhurana/OpenSpace
**Branch:** `main`
**Last updated:** 2026-04-21

---

## 1. What this is

Cleya is a **self-evolving autonomous agent company** with the explicit goal of hitting **₹41.5L (\$50K) MRR/month**. It spawns, kills, and mutates its own sub-agents based on KPIs. A human (you) watches from a Control Tower UI and intervenes only when needed.

### End-goal directives from the user (verbatim, do not violate)
1. "All agents should be using this no matter what LLM I am using — end goal is to reduce token cost across."
2. "Fully autonomous self-evolving, not just testing, but also trying to figure out new features… goal is to achieve \$50,000/month revenue."
3. "Full autonomy where credentials exist."
4. **Do NOT**: invent customer quotes, claim revenue not tied to Razorpay, spend money, or contact real humans without an `[APPROVED]` tag.
5. Daily targets: 50 DMs, 10 demos, 5 product improvements, 1 viral post.
6. Deploy mode: **Full ship — all services, AUTO mode.**

---

## 2. Live Services (Render)

**Render owner ID:** `tea-d6ueienfte5s738bncj0`
**Render API key:** `<redacted — in Render env>`

| Service ID | Name | Type | URL |
|---|---|---|---|
| `srv-d7jkd1t8nd3s73aavps0` | cleya-control-tower-api | Web (FastAPI) | https://cleya-control-tower-api.onrender.com |
| `srv-d7jkdjho3t8c73bpjin0` | cleya-control-tower-ui | Web (Next.js) | https://cleya-control-tower-ui.onrender.com |
| `srv-d7jkd3egvqtc73e726eg` | cleya-meta-agent | Background worker | — |
| `srv-d7jkd41j2pic739gq7d0` | cleya-worker-pool | Background worker | — |
| `srv-d7jkd51f9bms73ftkl6g` | cleya-tournament-runner | Background worker | — |
| `srv-d7jkd5ugvqtc73e728jg` | cleya-recruiter | Background worker | — |
| `crn-d7jkdh7lk1mc739emg90` | cleya-meta-learner | Cron (Sat 20:30 UTC) | — |
| `crn-d7jkdi3bc2fs739gm6qg` | cleya-skill-evolver | Cron (Sun 21:30 UTC) | — |
| `srv-d7j97l9kh4rs73fhcdt0` | cleya-founder-agent | Background worker (Growth L2, AGENT_ID `00000000-0000-0000-0000-000000000004`) | — |

All services pull from `github.com/visheshkhurana/OpenSpace` branch `main`, autoDeploy=yes.

### Render gotchas
- `runtime` must be `docker` (not `image`) when creating via API.
- Env var add uses `PUT /env-vars` with the **full array** (POST returns 405).
- Env var changes do NOT auto-redeploy — must POST to `/deploys` manually.
- API + UI share a single repo, but use different `rootDir`:
  - API + workers: `setup-kit/control-tower` with subdir Dockerfile paths (e.g. `./api/Dockerfile`)
  - UI: `setup-kit/control-tower-ui` with `./Dockerfile`

---

## 3. Credentials (preserve verbatim)

| Key | Value |
|---|---|
| Render API key | `<redacted — in Render env>` |
| Supabase project ID | `fhrynagbidbznfvuoxcn` (ap-south-1) |
| Supabase URL | `https://fhrynagbidbznfvuoxcn.supabase.co` |
| Supabase anon/service key (RLS disabled) | `<redacted — in Render env>` |
| CONTROL_TOWER_TOKEN (API bearer) | `<redacted — in Render env>` |
| Telegram bot handle | `@Vkjarvis1_bot` |
| Telegram bot token | `<redacted — in Render env>` |
| Telegram human chat ID | `6224744296` |
| OpenAI key | `<redacted — in Render env>` |

**Security note:** all creds currently live in Render env vars + Supabase. Rotate before going truly public.

---

## 4. Repo layout

```
setup-kit/
├── control-tower/                 ← backend services
│   ├── api/                       ← FastAPI (cleya-control-tower-api)
│   │   ├── main.py                ← ALL HTTP endpoints in one file (~1050 LOC)
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── meta/                      ← Meta Agent loop (spawns L2/L3, proposes tasks)
│   ├── worker/                    ← Generic task worker pool
│   ├── tournament/                ← Runs head-to-head agent tournaments
│   ├── recruiter/                 ← Posts/matches internal job board
│   ├── meta-learner/              ← Weekly: analyze KPIs, propose spawn rules
│   ├── skill-evolver/             ← Weekly: mutate skills, promote tournament winners
│   ├── shared/                    ← Shared Python libs (supabase client, openspace wrapper)
│   ├── host_skills/               ← 24 skill primitive definitions (.yaml + prompts)
│   ├── sql/                       ← Supabase migration SQL files
│   └── scripts/                   ← Seed scripts, ops helpers
│
└── control-tower-ui/              ← Next.js 14 dashboard (cleya-control-tower-ui)
    ├── src/app/                   ← Pages (/, /agents, /tasks, /metrics, /approvals, etc.)
    ├── src/components/
    │   ├── atoms/                 ← Buttons, badges, etc.
    │   ├── molecules/             ← MetricTile, MetaLearningCard, AgentNode, etc.
    │   └── organisms/             ← OrgTree, ActivityFeed, ApprovalsCarousel, AgentDrawer
    ├── src/hooks/                 ← React Query hooks (useAgents, useApprovals, etc.)
    ├── src/lib/
    │   ├── api.ts                 ← Fetch wrapper with token + unwrap helper
    │   ├── sse.ts                 ← EventSource wrapper for /feed
    │   ├── mock.ts                ← Mock data for local dev
    │   └── constants.ts           ← USE_MOCK flag, MRR_TARGET_INR
    ├── src/types/                 ← TypeScript types (Agent, Task, Approval, etc.)
    ├── .env.production            ← NEXT_PUBLIC_API_BASE + NEXT_PUBLIC_API_TOKEN
    └── Dockerfile
```

---

## 5. Database schema (Supabase, RLS disabled)

Main tables:

- **`agents`** — id, level (1/2/3), parent_id, type, status (pending/active/paused/killed/archived), skill_ref, goal, spawned_at, killed_at, kill_reason, revenue_contrib_inr, tasks_done, success_rate, created_by, metadata, version, parent_version_id, team_id, cost_to_date_inr, token_budget_weekly_inr, tournament_wins/losses, consecutive_kpi_weeks, founder_mode, last_active_at
- **`tasks`** — agent-assigned work units with status (queued/executing/done/failed), queued_at, completed_at, cost_inr
- **`skill_library`** — 24 seeded primitives (scraping, email_send, razorpay_listener, etc.)
- **`skill_versions`** — mutations of skills (skill-evolver creates these)
- **`tournaments`** — head-to-head matchups between skill variants
- **`approvals`** — human-in-loop gate queue for MANUAL/REVIEW mode
- **`meta_proposals`** — spawn-rule proposals from meta-learner
- **`agent_audit_log`** — every status change + action
- **`jobs`** — internal job board where L2 agents post, L3 agents pick up
- **`memories`** — agent long-term memory entries
- **`founder_mode_config`** — singleton row: mode (AUTO/REVIEW/MANUAL), global_pause

**Status CHECK constraint:** only `pending/active/paused/killed/archived`. Do NOT insert `idle` — it will fail.

---

## 6. API endpoints (cleya-control-tower-api)

All require `Authorization: Bearer <redacted — in Render env>` except `/healthz` and `/feed` (which accepts `?token=…` query param for SSE).

### Core
- `GET /healthz` — liveness + db + global_pause + founder_mode
- `GET /feed?token=…` — Server-Sent Events stream of ActivityEvents
- `GET /mode` and alias `GET /settings/mode` — current founder mode
- `POST /mode` — set AUTO / REVIEW / MANUAL

### Agents
- `GET /agents?level=&status=&limit=` — returns `{agents: [...], total}`
- `GET /agents/{id}` — returns `{agent, recent_tasks, recent_audit}`
- `POST /agents/compose` — spawn new agent from required_skills list
- `POST /agents/spawn` — direct spawn with explicit config
- `POST /agents/{id}/kill` — kill agent
- `POST /agents/{id}/rollback` — revert to a prior version
- `POST /agents/clone` — duplicate agent config
- `POST /agents/bulk-kill` — kill all below a success-rate threshold

### Metrics
- `GET /metrics` — legacy metrics blob
- `GET /metrics/overview` — UI tile data (MRR, leads, conv rate, active_agents, total_agents, tasks_completed_today, cost_inr_today/mtd)

### Meta-learning & approvals
- `GET /meta/summary` — `{proposals_pending, spawn_rules_proposed_this_week, avg_quality_delta_pct, last_proposal_at}`
- `POST /meta/tick` — force a meta-agent cycle
- `GET /approvals` — pending approvals
- `POST /approvals/{id}/approve` + `/deny`

### Other
- `GET /skills` and `/skills/library` — skill primitives
- `GET /jobs?status=open` — internal job board
- `POST /jobs` — post a new job
- `POST /jobs/{id}/force-pick` — manually assign
- `GET /tournaments` — history + active

---

## 7. How the system evolves itself

1. **Meta Agent** (continuous loop) — reads DB state, decides if new L3 agents should spawn, queues tasks, assigns to worker pool.
2. **Worker pool** — polls `tasks` table, picks queued tasks, executes via skill_ref, writes results back.
3. **Meta-learner** (weekly cron, Sun 02:00 IST) — reviews past week's KPIs per agent, proposes spawn rules, writes to `meta_proposals`.
4. **Skill-evolver** (weekly cron, Mon 03:00 IST) — for each L2 agent with <target metrics, generates a mutation of its skill, stores as new skill_version.
5. **Tournament runner** — pits skill_version candidates against each other on historical task replays. Winner gets promoted, losers archived.
6. **Recruiter** — maintains internal job board for cross-L2 coordination.
7. **Founder agent** (`srv-d7j97l9kh4rs73fhcdt0`) — the original seed agent, now graduated to Growth L2. Responsible for revenue-related tasks.

### Founder modes
- **AUTO** — Meta-agent executes proposals directly. Current setting.
- **REVIEW** — Proposals go to `/approvals` queue for human approval.
- **MANUAL** — Nothing spawns/kills without explicit human action.

Flip via: `POST /mode` with `{"mode": "REVIEW"}` or via the UI's header toggle.

---

## 8. Current state snapshot (as of handover)

- **11 agents** in DB (6 active, 1 paused, 4 killed with goal_complete)
- **MRR:** ₹13,560 (0.3% of ₹41.5L target)
- **Tasks completed today:** 8
- **Meta cycles run:** 1+ (spawned 4 L3 lead-gen agents, all completed goal)
- **Active L2 agents:** growth, analytics, recruiter (paused)
- **Active L1 agents:** meta, meta-learner, skill-evolver
- **Pending approvals:** 0
- **Open jobs:** 0

---

## 9. Known open issues / next steps

### Minor polish
1. **No real revenue yet** — Razorpay webhook watcher (agent `006`) is listening, but no test payment flowed through. First real ₹ requires a Razorpay Payment Link to be created by `growth` and delivered via outbound.
2. **Leads today = 0** — `growth` spawns L3 `growth-micro` agents that report `goal_complete` but tasks don't yet update the leads count. Need to wire task completion → `leads` table insert.
3. **Meta-learning summary** shows 0 pending (working as intended — first proposal hasn't generated yet because KPI week hasn't completed).
4. **Activity feed** says "Waiting for agent activity" despite SSE being connected — the backend's event broadcaster only emits on status transitions; add periodic heartbeat events so the feed feels alive.

### Architectural todos
1. **LLM cost arbitrage layer** — user's explicit end-goal: "reduce token cost across all LLMs." Currently all agents hard-call OpenAI. Build a router in `shared/` that routes per task-class to cheapest-adequate model (Gemini Flash for summarization, Sonnet for code, Haiku for classification, o1-mini for reasoning). Wire `cost_inr` tracking per task.
2. **Real outbound channels** — LinkedIn, X, Email. Currently `cold_outreach` skill is a no-op stub. Needs: API keys for each channel (Lemlist already connected), real send logic with `[APPROVED]` gate before first send to any new recipient.
3. **Payment link generation** — `growth` agent needs a skill to generate Razorpay payment links via API, embed in outreach.
4. **Retry / circuit breaker** on skill execution — currently a single OpenAI rate-limit error fails a task; should have exponential backoff.
5. **Agent version diffs in UI** — `/agents/{id}/versions` returns data but no UI page shows the diff between versions.

### Security/ops debt
1. Rotate the hardcoded CONTROL_TOWER_TOKEN.
2. Add rate limiting on public `/approvals/*/approve` endpoints.
3. Enable Supabase RLS and use a separate service key.
4. Move secrets out of Render env and into Vault/Doppler.

---

## 10. How to develop locally

```bash
# Clone
git clone https://github.com/visheshkhurana/OpenSpace
cd OpenSpace

# Backend (API)
cd setup-kit/control-tower/api
cp env.example .env  # fill in SUPABASE_URL, SUPABASE_KEY, CONTROL_TOWER_TOKEN, OPENAI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (UI)
cd setup-kit/control-tower-ui
cp env.example .env.local
# Edit .env.local:
#   NEXT_PUBLIC_API_BASE=http://localhost:8000
#   NEXT_PUBLIC_API_TOKEN=<redacted — in Render env>
npm install
npm run dev  # http://localhost:3000

# Run meta agent locally
cd setup-kit/control-tower/meta
python loop.py
```

### Env vars every service needs
- `SUPABASE_URL=https://fhrynagbidbznfvuoxcn.supabase.co`
- `SUPABASE_KEY=<anon key>`
- `CONTROL_TOWER_TOKEN=<redacted — in Render env>`
- `CONTROL_TOWER_API_URL=https://cleya-control-tower-api.onrender.com` (for workers)
- `OPENAI_API_KEY=<...>`
- `FOUNDER_MODE=AUTO`
- `GLOBAL_PAUSE=0`
- `TELEGRAM_BOT_TOKEN=...` (meta agent only, for human notifications)
- `TELEGRAM_CHAT_ID=6224744296` (meta agent only)

---

## 11. Operational runbook

### "The dashboard shows an error"
1. Hard refresh (Cmd+Shift+R) — Next.js ships aggressive caching.
2. Check `/healthz` — if `db:ok` and `status:ok`, API is fine.
3. Open devtools, check Network tab for 4xx/5xx. The three fixes shipped today were all shape mismatches between API + UI.

### "An agent is misbehaving"
1. Flip to REVIEW mode: `POST /mode {"mode":"REVIEW"}` or UI header.
2. Kill the specific agent: `POST /agents/{id}/kill` (appears immediately in audit log).
3. Emergency stop everything: set `GLOBAL_PAUSE=1` env var on meta + worker-pool services in Render, then manual redeploy.

### "I want to add a new skill"
1. Drop a new YAML file in `setup-kit/control-tower/host_skills/`.
2. Add a row to `skill_library` table (name, description, input_schema, output_schema).
3. Commit + push — next meta cycle will see it as available.

### "I want to manually spawn an agent"
`POST /agents/spawn` with body:
```json
{
  "level": 3,
  "type": "growth-micro",
  "parent_id": "00000000-0000-0000-0000-000000000004",
  "skill_ref": "cold_outreach",
  "goal": "Send 20 cold DMs to Y Combinator S26 founders",
  "token_budget_weekly_inr": 500
}
```

### "I want to scale workers"
Render dashboard → `cleya-worker-pool` → Scaling → bump `numInstances`. Tasks use Postgres advisory locks via `FOR UPDATE SKIP LOCKED` — safe to parallelize.

---

## 12. Critical files to read first

If you're Claude taking over this project, read these in order:

1. `HANDOVER.md` (this file)
2. `setup-kit/control-tower/api/main.py` — understand every endpoint
3. `setup-kit/control-tower/meta/loop.py` — the brain of the system
4. `setup-kit/control-tower/shared/*.py` — supabase client, LLM wrapper
5. `setup-kit/control-tower-ui/src/app/page.tsx` — dashboard composition
6. `setup-kit/control-tower-ui/src/lib/api.ts` — how the UI talks to the API
7. `setup-kit/control-tower/sql/*.sql` — full DB schema
8. `setup-kit/control-tower/host_skills/` — what the agents can actually do

---

## 13. Contact

- **Owner:** vysheshk@gmail.com
- **Telegram:** chat `6224744296`, bot `@Vkjarvis1_bot`

The bot posts status digests when meta cycles complete or when approvals are needed in REVIEW mode.

---

**End of handover.** System is running autonomously right now. If you pause it by mistake, flip `GLOBAL_PAUSE=0` and redeploy meta-agent + worker-pool.

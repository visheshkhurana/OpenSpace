# Cleya Control Tower

Autonomous AI Company OS for cleya.ai — self-spawning, self-evolving agents targeting ₹41.5L MRR.

## Architecture

```
control-tower/
├── api/                 # FastAPI orchestrator (all endpoints)
├── meta/                # Meta Agent (CEO AI) — runs every 1h
├── worker/              # Task queue worker pool — polls + executes skills
├── tournament/          # Tournament runner — judges agent competitions
├── meta-learner/        # Weekly pattern analysis (Sunday 09:00 IST)
├── skill-evolver/       # Weekly SKILL.md refinement (Monday 09:00 IST)
├── recruiter/           # Job marketplace worker (event-driven)
├── shared/              # Shared utilities (supabase, telegram, openspace)
├── host_skills/         # All 24+ SKILL.md files
├── sql/                 # Database migrations 001-004
└── scripts/             # Bootstrap, seed, smoke test
```

## Prerequisites

- Supabase project: `fhrynagbidbznfvuoxcn` (ap-south-1)
- OpenAI API key (gpt-4o-mini)
- Telegram bot token (for @Vkjarvis1_bot)
- Render account (Singapore region)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | `https://fhrynagbidbznfvuoxcn.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Yes | Service role key (not anon) |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `CONTROL_TOWER_TOKEN` | Yes | Bearer auth token for API |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `HUMAN_CHAT_ID` | No | Default: `6224744296` |
| `FOUNDER_MODE` | No | `AUTO` \| `REVIEW` \| `MANUAL` (default: `AUTO`) |
| `OPENSPACE_MODEL` | No | Default: `openai/gpt-4o-mini` |
| `GLOBAL_PAUSE` | No | `0` or `1` to halt all execution |
| `CONTROL_TOWER_API_URL` | Workers | `https://cleya-control-tower-api.onrender.com` |
| `CYCLE_INTERVAL_HOURS` | Meta | Default: `1` |
| `POLL_INTERVAL_SECONDS` | Worker | Default: `15` |
| `WORKER_ID` | Worker | Default: `worker-01` |

## Local Development

### 1. Set up environment

```bash
cp .env.example .env
# Fill in your values
export $(cat .env | xargs)
```

### 2. Run database migrations

```bash
# In Supabase SQL Editor, run in order:
# sql/001_init.sql
# sql/002_workforce_v2.sql
# sql/003_views.sql
# sql/004_seed.sql

# Or via bootstrap script:
python scripts/bootstrap.py
```

### 3. Seed skill library

```bash
pip install supabase
python scripts/seed_skill_library.py
```

### 4. Inject test metrics

```bash
python scripts/inject_test_metrics.py
```

### 5. Start API locally

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start worker locally

```bash
cd worker
pip install -r requirements.txt
python worker.py
```

### 7. Run smoke tests

```bash
export CONTROL_TOWER_API_URL=http://localhost:8000
export CONTROL_TOWER_TOKEN=your_token_here
python scripts/smoke_test.py
```

## Render Deploy

Each service maps to a directory:

| Render Service | Root Dir | Type | Plan |
|----------------|----------|------|------|
| `cleya-control-tower-api` | `setup-kit/control-tower/api` | Web | Starter |
| `cleya-meta-agent` | `setup-kit/control-tower/meta` | Worker | Starter + 1GB disk at `/data/meta` |
| `cleya-worker-pool` | `setup-kit/control-tower/worker` | Worker | Starter + 1GB disk at `/data/worker` |
| `cleya-tournament-runner` | `setup-kit/control-tower/tournament` | Worker | Starter |
| `cleya-meta-learner` | `setup-kit/control-tower/meta-learner` | Cron (Sun 09:00 IST) | Starter |
| `cleya-skill-evolver` | `setup-kit/control-tower/skill-evolver` | Cron (Mon 09:00 IST) | Starter |
| `cleya-recruiter` | `setup-kit/control-tower/recruiter` | Worker | Starter |

Each Dockerfile builds from `python:3.12-slim` and installs OpenSpace from GitHub.

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/healthz` | Health check | None |
| POST | `/agents/spawn` | Spawn new agent | Bearer |
| POST | `/agents/{id}/kill` | Kill agent | Bearer |
| GET | `/agents` | List agents | Bearer |
| GET | `/agents/{id}` | Agent detail | Bearer |
| POST | `/agents/compose` | Compose from skill primitives | Bearer |
| POST | `/agents/{id}/clone` | Clone agent + start tournament | Bearer |
| POST | `/agents/{id}/evolve` | Queue evolution | Bearer |
| POST | `/tasks` | Propose task | Bearer |
| GET | `/tasks` | List tasks | Bearer |
| GET | `/tasks/{id}` | Get task | Bearer |
| POST | `/tasks/{id}/execute` | Trigger execution | Bearer |
| POST | `/tasks/{id}/approve` | Approve HIGH-risk task | Bearer |
| POST | `/tasks/{id}/deny` | Deny HIGH-risk task | Bearer |
| GET | `/metrics` | Get latest metrics | Bearer |
| POST | `/metrics/ingest` | Write metric snapshot | Bearer |
| GET | `/feed` | SSE activity stream | Bearer |
| POST | `/meta/tick` | Meta Agent cycle context | Bearer |
| POST | `/telegram/webhook` | Telegram approval callbacks | None |
| GET | `/skills/library` | List skill primitives | Bearer |
| POST | `/skills/library` | Create skill primitive | Bearer |
| POST | `/tournaments` | Create tournament | Bearer |
| GET | `/tournaments/{id}` | Get tournament | Bearer |
| POST | `/tournaments/{id}/resolve` | Trigger judge | Bearer |
| POST | `/jobs` | Post job | Bearer |
| GET | `/jobs` | List jobs | Bearer |
| POST | `/jobs/{id}/apply` | Apply to job | Bearer |
| POST | `/jobs/{id}/select` | Select winner | Bearer |
| POST | `/teams` | Create team | Bearer |
| POST | `/teams/{id}/disband` | Disband team | Bearer |
| POST | `/memories` | Store memory | Bearer |
| GET | `/memories` | List memories | Bearer |
| GET | `/mode` | Get FOUNDER_MODE | Bearer |
| POST | `/mode` | Set FOUNDER_MODE | Bearer |

## Telegram Commands

| Command | Effect |
|---------|--------|
| `/mode auto` | Sets FOUNDER_MODE=AUTO (agents execute LOW immediately) |
| `/mode review` | Sets FOUNDER_MODE=REVIEW (LOW actions notify first) |
| `/mode manual` | Sets FOUNDER_MODE=MANUAL (all actions wait for [APPROVED]) |
| `GLOBAL_PAUSE=1` env | Halts all execution |

## Spec Gaps Filled

The following were not fully defined in the specs and were filled with sensible defaults:

1. **OpenSpace import**: `from openspace import OpenSpace, OpenSpaceConfig` — the exact API may differ; wrapped in try/except with graceful fallback
2. **Supabase RPC exec_sql**: Used for bootstrap — may need `pg_net` or direct psql for full migration support
3. **skill_library `tools` column**: Spec shows `ARRAY['http_get']` (Postgres array) but seeded as JSONB array `["http_get"]` for Supabase REST compatibility
4. **`agents.version` column**: Spec references as integer, not the `v1` string format from JSON schema — implemented as integer
5. **Memory embeddings**: `vector(1536)` column commented out in migration (requires pgvector extension to be manually enabled)
6. **Tournament runner**: Spec references `tournament_runner.resolve()` import — implemented as standalone service
7. **Metrics cron**: Not in the output layout spec; functionality covered by `inject_test_metrics.py` + agent-side `/metrics/ingest`
8. **`skill_library.tools` as JSONB**: Spec shows Postgres `ARRAY` type but Supabase REST API handles JSONB arrays better

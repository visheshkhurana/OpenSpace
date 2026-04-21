# Cleya Control Tower — UI

A live, Figma-grade dashboard for a self-evolving AI company. Next.js 14 App Router. Target: **₹41.5L MRR** (~$50K).

## Run locally (mock mode — no backend needed)

```bash
pnpm install
pnpm dev
# open http://localhost:3000
```

Mock mode is on by default (`NEXT_PUBLIC_USE_MOCK=true` is the fallback). Seeded with 6 agents, 10 tasks, 3 approvals, 3 proposals, 2 tournaments, and a looping SSE event replay every 3.5 s.

## Build for production

```bash
pnpm build
pnpm start
```

Next.js outputs to `.next/standalone`. The Dockerfile copies that into a slim Node 20 alpine image.

## Environment variables

Copy `env.example` → `.env.local` (for local) or set in Render dashboard.

| Var | Purpose |
|---|---|
| `NEXT_PUBLIC_USE_MOCK` | `true` serves seeded mock data. Flip to `false` when orchestrator is live. |
| `NEXT_PUBLIC_API_BASE` | FastAPI orchestrator base URL. |
| `NEXT_PUBLIC_API_TOKEN` | Bearer token. Personal dashboard — exposure acceptable. |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Anon key — RLS enforces read-only. |

## Deploy to Render

The Dockerfile is ready. From `setup-kit/control-tower-ui/`:

```bash
docker build -t cleya-control-tower .
docker run -p 3000:3000 cleya-control-tower
```

In Render:

1. New Web Service → Docker → point at this directory
2. Region: Singapore
3. Plan: Starter
4. Set all `NEXT_PUBLIC_*` vars above

## Routes

- `/` Dashboard — MRR hero, org tree, live feed, jobs, approvals
- `/agents` Individuals / Teams / Org tree (3-way toggle)
- `/tasks` Filterable table, batch actions
- `/metrics` MRR, leads, conv rate, revenue stack, economics tab
- `/approvals` Inbox with `A`/`D`/`S`/`J`/`K` hotkeys
- `/proposals` Meta-learner evolution inbox with skill diffs
- `/tournaments` Live races + diff modal
- `/skills` Skill primitive library
- `/memory` Memory vault with pin / decay
- `/settings` Mode switcher + diagnostics

## Stack

- Next.js 14 App Router, TypeScript strict
- Tailwind CSS + shadcn/ui primitives (unstyled — owned in-repo)
- Framer Motion v11 for motion
- @tanstack/react-query v5 for data fetching
- @supabase/supabase-js v2 for realtime
- Recharts v2 for charts
- lucide-react icons, Inter + JetBrains Mono fonts

## Project structure

```
src/
├── app/            # App Router pages
├── components/
│   ├── atoms/      # RiskBadge, LevelChip, StatusDot, …
│   ├── molecules/  # MetricTile, AgentNode, ApprovalCard, …
│   └── organisms/  # OrgTree, TopNav, AgentDrawer, TournamentArena, …
├── hooks/          # useAgents, useTasks, useProposals, …
├── lib/            # api, utils, mock, sse, supabase
├── providers/      # QueryProvider, RealtimeProvider
├── types/          # All TS interfaces from spec v1 + v2
└── styles/         # globals.css (Inter + JetBrains Mono + tokens)
```

# Cleya Founder Agent

Always-on, self-evolving autonomous founder agent for **Cleya.ai**.

## Mission

Get Cleya to **$50,000 MRR in 90 days**.

## How it runs

- Render Background Worker, Singapore region, Starter plan + 1GB persistent disk
- Wakes every `CYCLE_INTERVAL_HOURS` (default 3h)
- Each wake runs ONE OpenSpace cycle using the `cleya-founder` skill
- Journals to `/data/cleya/journal/`, persistent across deploys
- Sends Telegram messages only when blocked, when something noteworthy is found, or once daily at the 9am IST digest window

## Files on the persistent disk

```
/data/cleya/
  state.json            # cycle counter, MRR, last digest date
  journal/              # one md per cycle, append-only
  okrs.md
  product/{spec,roadmap,wow-moment,retention-hook}.md
  growth/{channels,funnel,icp,pricing-experiments}.md, drafts/
  research/{quotes,competitors,icp,india-context}.md
  finance/mrr.md
  ops/risks.md
  daily/<YYYY-MM-DD>.md
  ai-agents/<agent-name>/{spec,prompts,success-metric}.md
```

## Updating the skill

Edit `host_skills/cleya-founder/SKILL.md`, push to `main`. Render auto-deploys; the entrypoint refreshes the skill into `/data/openspace/host_skills/` on next boot.

## Observability

- Render dashboard: tail `app` logs
- Read journal: `/data/cleya/journal/*.md` from any container that has the disk mounted (or via Render shell)
- Cycle counter + MRR estimate: `state.json`

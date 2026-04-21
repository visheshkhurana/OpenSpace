"""
Cleya Control Tower — Meta-Learner (Weekly Cron)
================================================
Runs every Sunday 09:00 IST. Analyzes tournament outcomes, agent evolutions,
and revenue signals. Proposes changes to spawn_rules and skill_library.
All proposals are HIGH risk — require [APPROVED].

Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY,
     CONTROL_TOWER_API_URL, CONTROL_TOWER_TOKEN, OPENSPACE_MODEL,
     TELEGRAM_BOT_TOKEN, HUMAN_CHAT_ID
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client
import httpx

try:
    from openspace import OpenSpace, OpenSpaceConfig
except ImportError:
    OpenSpace = None
    OpenSpaceConfig = None

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
API_URL              = os.environ.get("CONTROL_TOWER_API_URL", "http://localhost:8000")
API_TOKEN            = os.environ.get("CONTROL_TOWER_TOKEN", "")
MODEL                = os.environ.get("OPENSPACE_MODEL", "openai/gpt-4o-mini")
TG_TOKEN             = os.environ.get("TELEGRAM_BOT_TOKEN", "")
HUMAN_CHAT_ID        = int(os.environ.get("HUMAN_CHAT_ID", "6224744296"))
SKILLS_ROOT          = Path(__file__).parent / "host_skills"

logging.basicConfig(level=logging.INFO, format='{"ts": "%(asctime)s", "msg": "%(message)s"}')
log = logging.getLogger("meta-learner")

db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def send_telegram(text: str):
    import urllib.request as ur
    if not TG_TOKEN:
        return
    payload = json.dumps({"chat_id": HUMAN_CHAT_ID, "text": text[:4000], "parse_mode": "Markdown"}).encode()
    req = ur.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=payload, headers={"Content-Type": "application/json"})
    try:
        with ur.urlopen(req, timeout=10): pass
    except Exception as e:
        log.error("telegram_failed error=%s", e)


async def run_weekly_analysis():
    """Execute one weekly meta-learner analysis cycle."""
    log.info("meta_learner_cycle_start")
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Gather data
    metrics = db.table("metrics").select("key, value, ts").gt("ts", week_ago.isoformat()).order("ts", desc=True).limit(500).execute().data or []
    tournaments = db.table("tournaments").select("*").gt("created_at", week_ago.isoformat()).execute().data or []
    evolutions = db.table("agent_evolutions").select("*").gt("created_at", week_ago.isoformat()).execute().data or []
    agents = db.table("agents").select("type, tasks_done, success_rate, revenue_contrib_inr, tournament_wins, tournament_losses").execute().data or []
    tasks = db.table("tasks").select("status, revenue_impact_score, risk_level").gt("queued_at", week_ago.isoformat()).execute().data or []

    skill_path = SKILLS_ROOT / "meta-learner" / "SKILL.md"
    skill_content = skill_path.read_text() if skill_path.exists() else "# Meta-Learner Skill\nAnalyze patterns and propose improvements."

    prompt = f"""You are the Meta-Learner for Cleya Control Tower.
{skill_content[:2000]}

---

WEEKLY ANALYSIS — {now.strftime('%Y-%m-%d')}

METRICS THIS WEEK:
{json.dumps(metrics[:50], indent=2)}

TOURNAMENTS THIS WEEK:
{json.dumps(tournaments, indent=2)}

AGENT EVOLUTIONS THIS WEEK:
{json.dumps(evolutions, indent=2)}

AGENT PERFORMANCE:
{json.dumps(agents, indent=2)}

TASK SUMMARY (last 7d):
- Total: {len(tasks)}
- Completed: {sum(1 for t in tasks if t['status'] == 'completed')}
- Failed: {sum(1 for t in tasks if t['status'] == 'failed')}
- Avg revenue impact: {sum(t['revenue_impact_score'] for t in tasks) / max(len(tasks), 1):.1f}

---

YOUR TASKS:
1. Identify the top 3 patterns from this week's data that explain revenue performance.
2. Propose 1-2 spawn_rule changes (metric thresholds that should be adjusted).
3. Identify any skill_library entries that should be updated or retired.
4. Propose any new spawn_rules needed based on observed patterns.

Format all proposals as:
<<<META_PROPOSAL>>>
{{
  "spawn_rule_changes": [...],
  "skill_library_changes": [...],
  "new_spawn_rules": [...],
  "reasoning": "..."
}}
<<<END_META_PROPOSAL>>>

Also send a weekly digest:
<<<TG_DIGEST>>>
📊 *Weekly Meta-Learner Report*
...
<<<END_TG_DIGEST>>>
"""

    if OpenSpace is None:
        log.warning("OpenSpace not installed — skipping meta-learner analysis")
        return

    try:
        cfg = OpenSpaceConfig(llm_model=MODEL)
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(prompt)
        response = result.get("response") or result.get("output") or ""

        if "<<<TG_DIGEST>>>" in response and "<<<END_TG_DIGEST>>>" in response:
            msg = response.split("<<<TG_DIGEST>>>")[1].split("<<<END_TG_DIGEST>>>")[0].strip()
            if msg:
                send_telegram(msg)

        if "<<<META_PROPOSAL>>>" in response and "<<<END_META_PROPOSAL>>>" in response:
            proposal = response.split("<<<META_PROPOSAL>>>")[1].split("<<<END_META_PROPOSAL>>>")[0].strip()
            send_telegram(f"📋 *META PROPOSAL* (requires [APPROVED])\n\n{proposal[:2000]}")
            log.info("meta_proposal_sent")

        log.info("meta_learner_cycle_complete")
    except Exception as e:
        log.exception("meta_learner_failed error=%s", e)


def is_sunday_0900_ist() -> bool:
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return now_ist.weekday() == 6 and now_ist.hour == 9 and now_ist.minute < 30


async def main():
    log.info("meta_learner_starting")
    last_run_date = None

    while True:
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        today = now_ist.date().isoformat()

        if is_sunday_0900_ist() and last_run_date != today:
            await run_weekly_analysis()
            last_run_date = today

        await asyncio.sleep(1800)  # check every 30 min


if __name__ == "__main__":
    # Can be run as a one-shot cron or as a loop
    if os.environ.get("RUN_ONCE", "0") == "1":
        asyncio.run(run_weekly_analysis())
    else:
        asyncio.run(main())

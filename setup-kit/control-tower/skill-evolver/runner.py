"""
Cleya Control Tower — Skill Evolver (Weekly Cron)
=================================================
Runs every Monday 09:00 IST. For each L2 agent with >=10 tasks completed,
drafts a refined SKILL.md variant (v+1) and enters it in a tournament vs parent.

Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY,
     CONTROL_TOWER_API_URL, CONTROL_TOWER_TOKEN, OPENSPACE_MODEL
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
MIN_TASKS_THRESHOLD  = int(os.environ.get("MIN_TASKS_THRESHOLD", "10"))

logging.basicConfig(level=logging.INFO, format='{"ts": "%(asctime)s", "msg": "%(message)s"}')
log = logging.getLogger("skill-evolver")

db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def api(method: str, path: str, **kwargs) -> dict:
    with httpx.Client(base_url=API_URL, headers=HEADERS, timeout=30) as c:
        resp = getattr(c, method)(path, **kwargs)
        resp.raise_for_status()
        return resp.json()


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


async def evolve_agent(agent: dict):
    """Draft a refined skill for one agent."""
    agent_id = agent["id"]
    skill_ref = agent["skill_ref"]
    log.info("evolving_agent id=%s type=%s tasks_done=%d", agent_id, agent["type"], agent["tasks_done"])

    skill_path = SKILLS_ROOT / skill_ref / "SKILL.md"
    current_skill = skill_path.read_text() if skill_path.exists() else ""

    # Get recent completed tasks for context
    recent_tasks = db.table("tasks").select("title, outputs, revenue_impact_score").eq("agent_id", agent_id).eq("status", "completed").order("completed_at", desc=True).limit(10).execute().data or []

    skill_evolver_path = SKILLS_ROOT / "skill-evolver" / "SKILL.md"
    evolver_skill = skill_evolver_path.read_text() if skill_evolver_path.exists() else ""

    prompt = f"""You are the Skill Evolver for Cleya Control Tower.
{evolver_skill[:1500]}

---
AGENT TO EVOLVE:
Type: {agent['type']} | Level: {agent['level']}
Tasks done: {agent['tasks_done']} | Success rate: {agent['success_rate']}%
Revenue contrib: ₹{agent['revenue_contrib_inr']:,}

CURRENT SKILL.md:
{current_skill[:2000]}

RECENT TASK OUTCOMES:
{json.dumps(recent_tasks[:5], indent=2)}

---

Draft an improved SKILL.md (v{agent.get('version', 1) + 1}) for this agent.
Focus on: what worked (keep), what didn't (fix), what's missing (add).
Output:
<<<EVOLVE_PROPOSAL agent_id={agent_id} from_version=v{agent.get('version', 1)} to_version=v{agent.get('version', 1) + 1}>>>
[complete new SKILL.md content here]
<<<END_EVOLVE_PROPOSAL>>>
"""

    if OpenSpace is None:
        log.warning("OpenSpace not available — skipping evolution for %s", agent_id)
        return

    try:
        cfg = OpenSpaceConfig(llm_model=MODEL)
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(prompt)
        response = result.get("response") or result.get("output") or ""

        import re
        for m in re.finditer(r'<<<EVOLVE_PROPOSAL\b[^>]*>>>', response):
            start_idx = m.end()
            remainder = response[start_idx:]
            if "<<<END_EVOLVE_PROPOSAL>>>" in remainder:
                content = remainder.split("<<<END_EVOLVE_PROPOSAL>>>", 1)[0].strip()

                evo_row = {
                    "agent_id": agent_id,
                    "from_version": agent.get("version", 1),
                    "to_version": agent.get("version", 1) + 1,
                    "change_summary": f"Weekly evolution cycle — {datetime.now(timezone.utc).date()}",
                    "reason": "Weekly skill-evolver cycle",
                    "perf_delta": {"success_rate": agent["success_rate"], "tasks_done": agent["tasks_done"]},
                    "status": "pending",
                }
                evo = db.table("agent_evolutions").insert(evo_row).execute().data[0]
                log.info("evolution_proposal_created agent=%s evo=%s", agent_id, evo["id"])

                send_telegram(f"🔄 *EVOLVE PROPOSAL* (MEDIUM risk)\nAgent: {agent['type']}\nVersion: v{evo_row['to_version']}\n\nApprove to apply to skill library.")
                break
    except Exception as e:
        log.exception("agent_evolution_failed agent=%s error=%s", agent_id, e)


async def run_evolution_cycle():
    """Main evolution cycle — process all eligible L2 agents."""
    log.info("skill_evolver_cycle_start")

    agents = db.table("agents")\
        .select("*")\
        .eq("status", "active")\
        .eq("level", 2)\
        .gte("tasks_done", MIN_TASKS_THRESHOLD)\
        .execute().data or []

    log.info("eligible_agents_for_evolution count=%d", len(agents))
    for agent in agents:
        await evolve_agent(agent)

    log.info("skill_evolver_cycle_complete evolved=%d", len(agents))


def is_monday_0900_ist() -> bool:
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return now_ist.weekday() == 0 and now_ist.hour == 9 and now_ist.minute < 30


async def main():
    log.info("skill_evolver_starting")
    last_run_date = None

    while True:
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        today = now_ist.date().isoformat()

        if is_monday_0900_ist() and last_run_date != today:
            await run_evolution_cycle()
            last_run_date = today

        await asyncio.sleep(1800)


if __name__ == "__main__":
    if os.environ.get("RUN_ONCE", "0") == "1":
        asyncio.run(run_evolution_cycle())
    else:
        asyncio.run(main())

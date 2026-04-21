"""
Cleya Control Tower — Recruiter
================================
Event-driven job marketplace worker. Polls for open job_posts, invites
active agents to bid, scores applications, recommends HIRE/REJECT.

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
POLL_S               = int(os.environ.get("RECRUITER_POLL_SECONDS", "60"))
SKILLS_ROOT          = Path(__file__).parent / "host_skills"

logging.basicConfig(level=logging.INFO, format='{"ts": "%(asctime)s", "msg": "%(message)s"}')
log = logging.getLogger("recruiter")

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


async def process_job(job: dict):
    """Process one open job post: invite bids, score, select."""
    job_id = job["id"]
    requirements = job.get("requirements", {})
    required_skills = requirements.get("skills", [])
    goal = requirements.get("goal", "")

    log.info("processing_job id=%s goal=%r", job_id, str(goal)[:60])

    # Notify active agents about the job
    active_agents = db.table("agents").select("id, type, metadata").eq("status", "active").execute().data or []
    for agent in active_agents:
        try:
            # Auto-apply from agents that may have relevant skills
            agent_skills_res = db.table("agent_skills").select("skill_id").eq("agent_id", agent["id"]).execute().data
            if not agent_skills_res and not required_skills:
                continue
            # Try to apply
            api("post", f"/jobs/{job_id}/apply", json={
                "agent_id": agent["id"],
                "pitch": f"Agent {agent['type']} applying with available capabilities for: {goal[:100]}",
                "estimated_cost_tokens": 5000,
                "estimated_quality": 7.0,
            })
        except Exception:
            pass

    # Wait for applications window then score
    await asyncio.sleep(5)

    applications = db.table("applications").select("*").eq("job_post_id", job_id).execute().data or []
    if not applications:
        log.info("job_no_applications id=%s — closing", job_id)
        db.table("job_posts").update({"status": "closed"}).eq("id", job_id).execute()
        return

    # Use recruiter skill to score applications
    recruiter_skill_path = SKILLS_ROOT / "recruiter" / "SKILL.md"
    recruiter_skill = recruiter_skill_path.read_text() if recruiter_skill_path.exists() else ""

    prompt = f"""You are the Recruiter agent for Cleya Control Tower.
{recruiter_skill[:1500]}

---
JOB POST:
{json.dumps(requirements, indent=2)}

APPLICATIONS ({len(applications)}):
{json.dumps(applications, indent=2)}

Score each applicant 1-10 for fit. Select the best one. Output:
<<<HIRE agent_id={{best_agent_id}} job_id={job_id} reasoning="...">
[hire recommendation]
<<<END_HIRE>>>
"""

    if OpenSpace is None:
        log.warning("OpenSpace not available — auto-selecting first applicant")
        selected = applications[0]["agent_id"]
    else:
        try:
            cfg = OpenSpaceConfig(llm_model=MODEL)
            async with OpenSpace(config=cfg) as cs:
                result = await cs.execute(prompt)
            response = result.get("response") or ""

            import re
            selected = applications[0]["agent_id"]
            for m in re.finditer(r'<<<HIRE\s+agent_id=([^\s]+)', response):
                selected = m.group(1).strip()
                break
        except Exception as e:
            log.error("recruiter_score_failed error=%s", e)
            selected = applications[0]["agent_id"]

    # Finalize selection
    try:
        api("post", f"/jobs/{job_id}/select", json={"agent_id": selected})
        send_telegram(f"👔 *HIRE* (HIGH risk — requires [APPROVED])\nJob: {goal[:100]}\nSelected agent: `{selected}`")
        log.info("job_filled id=%s winner=%s", job_id, selected)
    except Exception as e:
        log.error("job_fill_failed id=%s error=%s", job_id, e)


async def expire_old_jobs():
    """Expire jobs past their close time."""
    now = datetime.now(timezone.utc)
    jobs = db.table("job_posts").select("id, closes_at").eq("status", "open").execute().data or []
    for job in jobs:
        try:
            closes = datetime.fromisoformat(job["closes_at"].replace("Z", "+00:00"))
            if now > closes:
                db.table("job_posts").update({"status": "expired"}).eq("id", job["id"]).execute()
        except Exception:
            pass


async def run_loop():
    log.info("recruiter_starting")
    while True:
        try:
            await expire_old_jobs()
            open_jobs = db.table("job_posts").select("*").eq("status", "open").execute().data or []
            for job in open_jobs:
                await process_job(job)
        except Exception:
            log.exception("recruiter_loop_error")
        await asyncio.sleep(POLL_S)


if __name__ == "__main__":
    asyncio.run(run_loop())

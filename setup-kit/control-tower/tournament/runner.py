"""
Cleya Control Tower — Tournament Runner
========================================
Monitors open tournaments, runs the judge agent when all contestants complete,
declares winners, updates agent win/loss records.

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
POLL_S               = int(os.environ.get("TOURNAMENT_POLL_SECONDS", "60"))

logging.basicConfig(level=logging.INFO, format='{"ts": "%(asctime)s", "msg": "%(message)s"}')
log = logging.getLogger("tournament-runner")

db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def api(method: str, path: str, **kwargs) -> dict:
    with httpx.Client(base_url=API_URL, headers=HEADERS, timeout=30) as c:
        resp = getattr(c, method)(path, **kwargs)
        resp.raise_for_status()
        return resp.json()


async def judge_tournament(tournament: dict):
    """Run the judge agent on a tournament."""
    tid = tournament["id"]
    log.info("judging_tournament id=%s", tid)

    entries = db.table("tournament_entries").select("*").eq("tournament_id", tid).execute().data
    if not entries:
        log.warning("tournament_no_entries id=%s", tid)
        return

    # Collect outputs from each contestant's completed task
    contestant_outputs = []
    for entry in entries:
        if entry.get("output_id"):
            task = db.table("tasks").select("outputs, agent_id, title").eq("id", entry["output_id"]).single().execute().data
            if task:
                contestant_outputs.append({
                    "agent_id": entry["agent_id"],
                    "task_title": task.get("title", ""),
                    "outputs": task.get("outputs", {}),
                })

    if not contestant_outputs:
        log.warning("tournament_no_outputs id=%s", tid)
        return

    criteria = tournament.get("judge_criteria", {"quality": 0.5, "cost": 0.3, "speed": 0.2})
    prompt = f"""You are the Judge agent for Cleya Control Tower tournament {tid}.

TOURNAMENT CRITERIA:
{json.dumps(criteria, indent=2)}

CONTESTANT OUTPUTS:
{json.dumps(contestant_outputs, indent=2)}

Your job: Score each contestant on each criterion (0-10). Declare a winner.

Output in this EXACT format:
<<<JUDGE_RESULT>>>
{{
  "winner_agent_id": "<uuid>",
  "scores": [
    {{"agent_id": "<uuid>", "total": 8.5, "quality": 9, "cost": 8, "speed": 8}},
    ...
  ],
  "rubric": {{"reasoning": "one sentence per contestant on why winner won"}}
}}
<<<END_JUDGE_RESULT>>>
"""
    if OpenSpace is None:
        log.warning("OpenSpace not installed — skipping tournament judge")
        return

    try:
        cfg = OpenSpaceConfig(llm_model=MODEL)
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(prompt)
        response = result.get("response") or result.get("output") or ""

        if "<<<JUDGE_RESULT>>>" in response and "<<<END_JUDGE_RESULT>>>" in response:
            raw = response.split("<<<JUDGE_RESULT>>>")[1].split("<<<END_JUDGE_RESULT>>>")[0].strip()
            verdict = json.loads(raw)
            winner_id = verdict.get("winner_agent_id")

            # Update tournament
            db.table("tournaments").update({
                "status": "resolved",
                "winner_agent_id": winner_id,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", tid).execute()

            # Update entry scores
            for s in verdict.get("scores", []):
                db.table("tournament_entries").update({
                    "score": s.get("total"),
                    "rubric": s,
                }).eq("tournament_id", tid).eq("agent_id", s["agent_id"]).execute()

            # Update agent win/loss
            for entry in entries:
                aid = entry["agent_id"]
                if aid == winner_id:
                    agent = db.table("agents").select("tournament_wins").eq("id", aid).single().execute().data
                    if agent:
                        db.table("agents").update({"tournament_wins": agent["tournament_wins"] + 1}).eq("id", aid).execute()
                else:
                    agent = db.table("agents").select("tournament_losses").eq("id", aid).single().execute().data
                    if agent:
                        db.table("agents").update({"tournament_losses": agent["tournament_losses"] + 1}).eq("id", aid).execute()

            log.info("tournament_resolved id=%s winner=%s", tid, winner_id)
    except Exception as e:
        log.exception("judge_failed tournament=%s error=%s", tid, e)
        db.table("tournaments").update({"status": "expired"}).eq("id", tid).execute()


async def expire_stale_tournaments():
    """Mark timed-out tournaments as expired."""
    tournaments = db.table("tournaments").select("*").eq("status", "open").execute().data
    now = datetime.now(timezone.utc)
    for t in (tournaments or []):
        try:
            created_at = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            time_box = timedelta(hours=t.get("time_box_hours", 48))
            if now - created_at > time_box:
                db.table("tournaments").update({"status": "expired"}).eq("id", t["id"]).execute()
                log.info("tournament_expired id=%s", t["id"])
        except Exception:
            pass


async def run_loop():
    log.info("tournament_runner_starting")
    while True:
        try:
            await expire_stale_tournaments()

            judging = db.table("tournaments").select("*").eq("status", "judging").execute().data
            for t in (judging or []):
                await judge_tournament(t)

        except Exception:
            log.exception("tournament_runner_error")

        await asyncio.sleep(POLL_S)


if __name__ == "__main__":
    asyncio.run(run_loop())

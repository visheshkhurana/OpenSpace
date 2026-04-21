"""
Cleya Control Tower — Worker Pool
==================================
Polls Supabase tasks table, claims tasks with SKIP LOCKED,
invokes OpenSpace skill engine, writes outputs, updates state.

One process = one worker. Run N instances for N-parallel execution.
Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY,
     TELEGRAM_BOT_TOKEN, HUMAN_CHAT_ID, OPENSPACE_MODEL,
     POLL_INTERVAL_SECONDS, GLOBAL_PAUSE, WORKER_ID
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add shared/ to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client, Client

try:
    from openspace import OpenSpace, OpenSpaceConfig
except ImportError:
    OpenSpace = None
    OpenSpaceConfig = None

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
OPENAI_KEY           = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "")
HUMAN_CHAT_ID        = int(os.environ.get("HUMAN_CHAT_ID", "6224744296"))
MODEL                = os.environ.get("OPENSPACE_MODEL", "openai/gpt-4o-mini")
POLL_INTERVAL_S      = int(os.environ.get("POLL_INTERVAL_SECONDS", "15"))
GLOBAL_PAUSE         = os.environ.get("GLOBAL_PAUSE", "0") == "1"
WORKER_ID            = os.environ.get("WORKER_ID", "worker-01")

SKILLS_ROOT = Path(__file__).parent / "host_skills"

logging.basicConfig(
    level=logging.INFO,
    format='{"ts": "%(asctime)s", "level": "%(levelname)s", "worker": "' + WORKER_ID + '", "msg": "%(message)s"}',
)
log = logging.getLogger("worker")

db: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ── Helpers ───────────────────────────────────────────────────────────────────

def audit(agent_id: str, event: str, payload: dict):
    try:
        db.table("agent_audit_log").insert({
            "agent_id": agent_id,
            "event": event,
            "payload": payload,
            "worker_id": WORKER_ID,
        }).execute()
    except Exception as e:
        log.error("audit_failed event=%s error=%s", event, e)


def send_telegram(text: str):
    import urllib.request as ur
    if not TELEGRAM_TOKEN:
        return
    payload = json.dumps({
        "chat_id": HUMAN_CHAT_ID,
        "text": text[:4000],
        "parse_mode": "Markdown",
    }).encode()
    req = ur.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with ur.urlopen(req, timeout=10):
            pass
    except Exception as e:
        log.error("telegram_failed error=%s", e)


def resolve_skill(skill_ref: str) -> str:
    """Resolve skill_ref to SKILL.md content."""
    skill_path = SKILLS_ROOT / skill_ref / "SKILL.md"
    if not skill_path.exists():
        fallback = Path("/data/worker/host_skills") / skill_ref / "SKILL.md"
        if fallback.exists():
            return fallback.read_text()
        raise FileNotFoundError(
            f"SKILL.md not found for skill_ref='{skill_ref}' (checked {skill_path} and {fallback})"
        )
    return skill_path.read_text()


def extract_tg_markers(text: str) -> list:
    """Extract all <<<TG_*>>> markers from LLM output. Returns [(kind, message)]."""
    found = []
    for kind, start, end in [
        ("DIGEST",    "<<<TG_DIGEST>>>",    "<<<END_TG_DIGEST>>>"),
        ("BLOCKED",   "<<<TG_BLOCKED>>>",   "<<<END_TG_BLOCKED>>>"),
        ("DISCOVERY", "<<<TG_DISCOVERY>>>", "<<<END_TG_DISCOVERY>>>"),
    ]:
        if start in text and end in text:
            msg = text.split(start, 1)[1].split(end, 1)[0].strip()
            if msg:
                found.append((kind, msg))
    return found


def extract_marker(text: str, start: str, end: str) -> list:
    """Extract all occurrences of a marker pair."""
    results = []
    parts = text.split(start)
    for part in parts[1:]:
        if end in part:
            results.append(part.split(end, 1)[0].strip())
    return results


def claim_task() -> dict | None:
    """Claim one queued task with SKIP LOCKED semantics via RPC."""
    try:
        result = db.rpc("claim_next_task", {"p_worker_id": WORKER_ID}).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        log.error("claim_task_failed error=%s", e)
    return None


def update_task_claimed(task_id: str):
    db.table("tasks").update({
        "status": "claimed",
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "worker_id": WORKER_ID,
    }).eq("id", task_id).execute()


def update_task_executing(task_id: str):
    db.table("tasks").update({"status": "executing"}).eq("id", task_id).execute()


def update_task_completed(task_id: str, outputs: dict, revenue_contrib: int = 0):
    db.table("tasks").update({
        "status": "completed",
        "outputs": outputs,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task_id).execute()

    task_res = db.table("tasks").select("agent_id, revenue_impact_score").eq("id", task_id).single().execute()
    if task_res.data:
        agent_id = task_res.data["agent_id"]
        try:
            db.rpc("increment_agent_stats", {"p_agent_id": agent_id, "p_revenue_inr": revenue_contrib}).execute()
        except Exception as e:
            log.warning("increment_stats_rpc_failed error=%s — using direct update", e)
            agent = db.table("agents").select("tasks_done, revenue_contrib_inr").eq("id", agent_id).single().execute().data
            if agent:
                db.table("agents").update({
                    "tasks_done": agent["tasks_done"] + 1,
                    "revenue_contrib_inr": agent["revenue_contrib_inr"] + revenue_contrib,
                }).eq("id", agent_id).execute()


def update_task_failed(task_id: str, error: str, retry: bool):
    update = {
        "status": "failed" if not retry else "queued",
        "error_message": error,
    }
    db.table("tasks").update(update).eq("id", task_id).execute()
    try:
        db.rpc("increment_task_retry", {"p_task_id": task_id}).execute()
    except Exception:
        pass


def maybe_kill_micro_agent(agent: dict):
    """Level-3 agents auto-kill after their single task is done."""
    if agent.get("level") == 3:
        db.table("agents").update({
            "status": "killed",
            "killed_at": datetime.now(timezone.utc).isoformat(),
            "kill_reason": "goal_complete",
        }).eq("id", agent["id"]).execute()
        audit(agent["id"], "killed", {"reason": "goal_complete", "auto": True})
        log.info("micro_agent_auto_killed id=%s", agent["id"])


def handle_special_markers(response: str, agent_id: str, task_id: str):
    """Handle META_PROPOSAL, EVOLVE_PROPOSAL, HIRE, JUDGE_RESULT, NEW_SKILL markers."""
    # META_PROPOSAL
    for content in extract_marker(response, "<<<META_PROPOSAL>>>", "<<<END_META_PROPOSAL>>>"):
        audit(agent_id, "meta_proposal_emitted", {"task_id": task_id, "proposal": content[:500]})
        send_telegram(f"📋 *META PROPOSAL* (requires [APPROVED])\n\n{content[:1000]}")

    # JUDGE_RESULT
    for content in extract_marker(response, "<<<JUDGE_RESULT>>>", "<<<END_JUDGE_RESULT>>>"):
        audit(agent_id, "judge_result_emitted", {"task_id": task_id, "result": content[:500]})
        try:
            parsed = json.loads(content)
            winner_id = parsed.get("winner_agent_id")
            if winner_id:
                tournament_res = db.table("tournament_entries").select("tournament_id").eq("agent_id", str(winner_id)).limit(1).execute()
                if tournament_res.data:
                    tid = tournament_res.data[0]["tournament_id"]
                    db.table("tournaments").update({"status": "resolved", "winner_agent_id": str(winner_id), "resolved_at": datetime.now(timezone.utc).isoformat()}).eq("id", tid).execute()
        except Exception as e:
            log.warning("judge_result_parse_failed error=%s", e)

    # NEW_SKILL
    import re
    for m in re.finditer(r'<<<NEW_SKILL\b[^>]*>>>', response):
        start_idx = m.end()
        remainder = response[start_idx:]
        if "<<<END_NEW_SKILL>>>" in remainder:
            content = remainder.split("<<<END_NEW_SKILL>>>", 1)[0].strip()
            audit(agent_id, "new_skill_proposed", {"task_id": task_id, "content": content[:500]})
            send_telegram(f"🆕 *NEW SKILL PROPOSED*\n\n{content[:1000]}\n\n[MEDIUM risk — approve to add to library]")

    # HIRE marker
    for m in re.finditer(r'<<<HIRE\b[^>]*>>>', response):
        start_idx = m.end()
        remainder = response[start_idx:]
        if "<<<END_HIRE>>>" in remainder:
            content = remainder.split("<<<END_HIRE>>>", 1)[0].strip()
            audit(agent_id, "hire_recommendation", {"task_id": task_id, "hire": content[:500]})
            send_telegram(f"👔 *HIRE RECOMMENDATION* (HIGH risk — requires [APPROVED])\n\n{content[:1000]}")

    # EVOLVE_PROPOSAL
    for m in re.finditer(r'<<<EVOLVE_PROPOSAL\b[^>]*>>>', response):
        start_idx = m.end()
        remainder = response[start_idx:]
        if "<<<END_EVOLVE_PROPOSAL>>>" in remainder:
            content = remainder.split("<<<END_EVOLVE_PROPOSAL>>>", 1)[0].strip()
            audit(agent_id, "evolve_proposal_emitted", {"task_id": task_id, "proposal": content[:500]})
            send_telegram(f"🔄 *EVOLVE PROPOSAL* [MEDIUM risk]\n\n{content[:1000]}")


# ── Core execution ────────────────────────────────────────────────────────────

async def execute_task(task: dict):
    """Full execution pipeline for one task."""
    task_id  = task["id"]
    agent_id = task["agent_id"]

    agent_res = db.table("agents").select("*").eq("id", agent_id).single().execute()
    if not agent_res.data:
        log.error("task_execute_no_agent task=%s agent=%s", task_id, agent_id)
        update_task_failed(task_id, "Agent not found", retry=False)
        return

    agent = agent_res.data
    update_task_claimed(task_id)
    audit(agent_id, "task_claimed", {"task_id": task_id, "worker_id": WORKER_ID})
    log.info("task_claimed id=%s title=%r agent_type=%s", task_id, task["title"][:60], agent["type"])

    try:
        skill_content = resolve_skill(agent["skill_ref"])

        prompt = f"""You are a Cleya Control Tower agent.

AGENT TYPE: {agent['type']} (Level {agent['level']})
AGENT GOAL: {agent['goal']}
SKILL CONTEXT:
{skill_content[:3000]}

---

CURRENT TASK:
Title: {task['title']}
Proposed Action: {task['proposed_action']}
Inputs: {json.dumps(task['inputs'], indent=2)}

Revenue Impact Score: {task['revenue_impact_score']}/10
Urgency: {task['urgency']}/10
Confidence: {task['confidence']}/10

---

INSTRUCTIONS:
1. Execute the task described above. Do the actual work.
2. Answer: "How does this increase revenue?" with specific, measurable actions.
3. Write all outputs as structured JSON that can be stored.
4. If you need to send a Telegram notification, use the markers:
   - For discovery/opportunity: <<<TG_DISCOVERY>>> message <<<END_TG_DISCOVERY>>>
   - If blocked and need human input: <<<TG_BLOCKED>>> message <<<END_TG_BLOCKED>>>
5. End with <COMPLETE> when done.
6. Estimate revenue contribution in INR from completing this task.

OUTPUT FORMAT (at end, after all work):
<<<OUTPUT_JSON>>>
{{
  "summary": "one line summary of what was done",
  "artifacts": {{ }},
  "revenue_contribution_inr": 0,
  "next_actions": ["action1", "action2"]
}}
<<<END_OUTPUT_JSON>>>
"""

        update_task_executing(task_id)

        if OpenSpace is None:
            raise RuntimeError("OpenSpace not installed — cannot execute task")

        cfg = OpenSpaceConfig(llm_model=MODEL)
        start_time = time.time()
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(prompt)
        elapsed = time.time() - start_time

        response = result.get("response") or result.get("output") or ""
        log.info("task_executed id=%s chars=%d elapsed=%.1fs", task_id, len(response), elapsed)

        outputs = {"raw_response": response[:10000]}
        revenue_inr = 0
        if "<<<OUTPUT_JSON>>>" in response and "<<<END_OUTPUT_JSON>>>" in response:
            try:
                json_str = response.split("<<<OUTPUT_JSON>>>")[1].split("<<<END_OUTPUT_JSON>>>")[0].strip()
                parsed = json.loads(json_str)
                outputs = parsed
                revenue_inr = int(parsed.get("revenue_contribution_inr", 0))
            except (json.JSONDecodeError, ValueError) as e:
                log.warning("output_json_parse_failed task=%s error=%s", task_id, e)

        for kind, msg in extract_tg_markers(response):
            prefix = {"DIGEST": "📊", "BLOCKED": "🚫 *BLOCKED*", "DISCOVERY": "🎯 *DISCOVERY*"}.get(kind, kind)
            send_telegram(f"{prefix}\n\n{msg}")
            audit(agent_id, f"tg_{kind.lower()}_sent", {"task_id": task_id, "preview": msg[:100]})

        handle_special_markers(response, agent_id, task_id)

        update_task_completed(task_id, outputs, revenue_inr)
        audit(agent_id, "task_completed", {"task_id": task_id, "revenue_inr": revenue_inr, "elapsed_s": round(elapsed, 1)})
        log.info("task_completed id=%s revenue_inr=%d", task_id, revenue_inr)

        maybe_kill_micro_agent(agent)

    except FileNotFoundError as e:
        log.error("skill_not_found task=%s error=%s", task_id, e)
        update_task_failed(task_id, str(e), retry=False)
        audit(agent_id, "task_failed", {"task_id": task_id, "error": str(e)})

    except Exception as e:
        log.exception("task_execution_error task=%s", task_id)
        retry = task.get("retry_count", 0) < task.get("max_retries", 2)
        update_task_failed(task_id, str(e), retry=retry)
        audit(agent_id, "task_failed", {"task_id": task_id, "error": str(e)[:500], "will_retry": retry})


# ── Main poll loop ────────────────────────────────────────────────────────────

async def poll_loop():
    log.info("worker_started id=%s model=%s poll_interval=%ds", WORKER_ID, MODEL, POLL_INTERVAL_S)
    empty_polls = 0
    max_backoff = 60

    while True:
        if os.environ.get("GLOBAL_PAUSE", "0") == "1":
            log.info("global_pause_active sleeping 30s")
            await asyncio.sleep(30)
            continue

        task = claim_task()

        if task is None:
            empty_polls += 1
            sleep_s = min(POLL_INTERVAL_S * (2 ** min(empty_polls - 1, 2)), max_backoff)
            await asyncio.sleep(sleep_s)
            continue

        empty_polls = 0
        try:
            await execute_task(task)
        except Exception:
            log.exception("unhandled_error_in_execute_task task=%s", task.get("id"))

        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(poll_loop())

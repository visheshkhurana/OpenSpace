"""
Cleya Control Tower — Meta Agent (CEO AI, Level 1)
===================================================
Runs every CYCLE_INTERVAL_HOURS. Reads metrics, evaluates spawn rules,
spawns/kills agents, proposes tasks, emits daily digest to Telegram.

Env: CONTROL_TOWER_API_URL, CONTROL_TOWER_TOKEN, OPENAI_API_KEY,
     TELEGRAM_BOT_TOKEN, HUMAN_CHAT_ID, CYCLE_INTERVAL_HOURS,
     OPENSPACE_MODEL, GLOBAL_PAUSE
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

import httpx

try:
    from openspace import OpenSpace, OpenSpaceConfig
except ImportError:
    OpenSpace = None
    OpenSpaceConfig = None

# ── Config ────────────────────────────────────────────────────────────────────
API_URL        = os.environ["CONTROL_TOWER_API_URL"]
API_TOKEN      = os.environ["CONTROL_TOWER_TOKEN"]
OPENAI_KEY     = os.environ["OPENAI_API_KEY"]
TG_TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "")
HUMAN_CHAT_ID  = int(os.environ.get("HUMAN_CHAT_ID", "6224744296"))
INTERVAL_HOURS = float(os.environ.get("CYCLE_INTERVAL_HOURS", "1"))
MODEL          = os.environ.get("OPENSPACE_MODEL", "openai/gpt-4o-mini")
SKILLS_ROOT    = Path(__file__).parent / "host_skills"
META_SKILL_REF = "meta-agent"
STATE_FILE     = Path("/data/meta/meta_state.json")

logging.basicConfig(
    level=logging.INFO,
    format='{"ts": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}',
)
log = logging.getLogger("meta-agent")

# ── API Client ────────────────────────────────────────────────────────────────
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def api(method: str, path: str, **kwargs) -> dict:
    """Synchronous API call wrapper."""
    with httpx.Client(base_url=API_URL, headers=HEADERS, timeout=30) as client:
        resp = getattr(client, method)(path, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        s = {
            "cycle_number": 0,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_cycle_at_utc": None,
            "last_digest_date_ist": None,
            "total_agents_spawned": 0,
            "total_agents_killed": 0,
        }
        STATE_FILE.write_text(json.dumps(s, indent=2))
    return json.loads(STATE_FILE.read_text())


def save_state(s: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, indent=2))


def in_digest_window(now_utc: datetime) -> bool:
    """09:00–09:29 IST = 03:30–03:59 UTC."""
    ist = now_utc + timedelta(hours=5, minutes=30)
    return ist.hour == 9 and ist.minute < 30


def send_telegram(text: str):
    import urllib.request as ur
    if not TG_TOKEN:
        return
    payload = json.dumps({
        "chat_id": HUMAN_CHAT_ID,
        "text": text[:4000],
        "parse_mode": "Markdown",
    }).encode()
    req = ur.Request(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with ur.urlopen(req, timeout=10):
            pass
    except Exception as e:
        log.error("telegram_send_failed error=%s", e)


# ── Cycle Logic ───────────────────────────────────────────────────────────────

async def run_meta_cycle(state: dict) -> dict:
    """One full Meta Agent cycle."""
    cycle = state["cycle_number"] + 1
    now   = datetime.now(timezone.utc)
    log.info("meta_cycle_start cycle=%d", cycle)

    # ── Step 1: Get context from API ──────────────────────────────────────────
    tick_res = api("post", "/meta/tick", json={
        "cycle_number": cycle,
        "notes": f"Meta agent cycle {cycle}",
    })
    if tick_res.get("system_status") == "paused":
        log.info("system_paused skipping_cycle")
        return state

    metrics       = tick_res.get("metrics", {})
    active_agents = tick_res.get("active_agents", [])
    triggered     = tick_res.get("triggered_rules", [])
    pending_appr  = tick_res.get("pending_approvals", [])

    log.info(
        "tick_context metrics=%d active_agents=%d triggered_rules=%d pending=%d",
        len(metrics), len(active_agents), len(triggered), len(pending_appr),
    )

    # ── Step 2: Auto-approve MEDIUM tasks older than 2 hours ─────────────────
    for appr in pending_appr:
        try:
            task_res = api("get", f"/tasks/{appr['task_id']}")
            if task_res.get("risk_level") == "MEDIUM":
                sent_at_str = appr.get("sent_at", "")
                if sent_at_str:
                    sent_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00"))
                    hours_waiting = (now - sent_at).total_seconds() / 3600
                    if hours_waiting >= 2:
                        api("post", f"/tasks/{appr['task_id']}/approve",
                            params={"approved_by": "auto:2h_timeout"})
                        log.info("medium_task_auto_approved task=%s", appr["task_id"])
        except Exception as e:
            log.error("auto_approve_failed task=%s error=%s", appr.get("task_id"), e)

    # ── Step 3: Fire triggered spawn rules ────────────────────────────────────
    spawned_this_cycle = []
    for rule in triggered:
        agent_type = rule["agent_type_to_spawn"]
        active_of_type = [a for a in active_agents if a["type"] == agent_type]
        if active_of_type:
            log.info("rule_skipped type=%s already_active=True", agent_type)
            continue

        goal = rule["goal_template"].replace("{{.value}}", str(rule["current_value"]))
        level = 3 if "micro" in agent_type else 2

        # Map agent types to skill refs
        skill_map = {
            "growth": "lead-gen",
            "sales": "outreach",
            "product": "ux",
            "data": "analytics",
        }
        skill_ref = skill_map.get(agent_type, agent_type)

        try:
            spawn_res = api("post", "/agents/spawn", json={
                "parent_id": None,
                "type": agent_type,
                "goal": goal,
                "skill_ref": skill_ref,
                "level": level,
                "created_by": "meta",
            })
            spawned_this_cycle.append(spawn_res["agent_id"])
            state["total_agents_spawned"] += 1
            log.info("rule_fired_spawn rule=%r agent_id=%s type=%s",
                     rule["name"], spawn_res["agent_id"], agent_type)

            api("post", "/metrics/ingest", json={
                "key": f"rule_fired:{rule.get('rule_id', rule['name'])}",
                "value": 1,
                "source": "meta",
                "metadata": {"rule_name": rule["name"]},
            })
        except Exception as e:
            log.error("spawn_failed rule=%r error=%s", rule["name"], e)

    # ── Step 4: Cull agents with poor performance ─────────────────────────────
    cull_candidates = []
    for agent in active_agents:
        if (agent.get("level") in (2, 3)
                and agent.get("tasks_done", 0) >= 5
                and agent.get("success_rate", 100) < 20.0):
            cull_candidates.append(agent)

    for agent in cull_candidates:
        try:
            api("post", f"/agents/{agent['id']}/kill",
                params={"reason": "below_success_threshold"})
            state["total_agents_killed"] += 1
            log.info("agent_culled id=%s type=%s", agent["id"], agent["type"])
        except Exception as e:
            log.error("cull_failed agent=%s error=%s", agent["id"], e)

    # ── Step 5: Build Meta Agent prompt for LLM strategic decisions ───────────
    skill_path = SKILLS_ROOT / META_SKILL_REF / "SKILL.md"
    skill_content = skill_path.read_text() if skill_path.exists() else "# Meta Agent Skill\nOrchestrate agents for revenue."

    prompt = f"""You are the Meta Agent — CEO AI of Cleya Control Tower.

{skill_content[:4000]}

---

CURRENT CYCLE: {cycle}
TIMESTAMP: {now.isoformat()}

METRICS SNAPSHOT:
{json.dumps(metrics, indent=2)}

ACTIVE AGENTS ({len(active_agents)}):
{json.dumps(active_agents, indent=2)}

TRIGGERED SPAWN RULES THIS CYCLE:
{json.dumps(triggered, indent=2)}

AGENTS SPAWNED THIS CYCLE: {spawned_this_cycle}

PENDING APPROVALS: {len(pending_appr)}

---

YOUR TASKS THIS CYCLE:

1. Assess: Are we on track to ₹41.5L MRR? What is the single biggest bottleneck?
2. Prioritize: List the top 3 actions that will move revenue TODAY.
3. Spawn (if needed): Propose any additional agents with this format:
   <<<SPAWN>>>
   {{
     "type": "growth-micro",
     "goal": "specific goal",
     "skill_ref": "lead-gen",
     "level": 3,
     "reason": "why this helps revenue",
     "revenue_impact_score": 7,
     "urgency": 8,
     "confidence": 7
   }}
   <<<END_SPAWN>>>

4. Kill (if needed): Propose agents to kill:
   <<<KILL>>>
   {{ "agent_id": "uuid", "reason": "why" }}
   <<<END_KILL>>>

5. Propose tasks for active agents:
   <<<TASK>>>
   {{
     "agent_id": "uuid of existing active agent",
     "title": "task title",
     "proposed_action": "what to do",
     "risk_level": "LOW",
     "revenue_impact_score": 7,
     "urgency": 6,
     "confidence": 8
   }}
   <<<END_TASK>>>

6. Daily digest (only at 09:00 IST):
   <<<TG_DIGEST>>>
   📊 *Cleya Daily Digest*
   ...
   <<<END_TG_DIGEST>>>

Remember: Every action must answer "How does this increase revenue?"
Revenue scores below 3 will be rejected.

End with <COMPLETE>.
"""

    # ── Step 6: Invoke OpenSpace ──────────────────────────────────────────────
    if OpenSpace is None:
        log.warning("OpenSpace not installed — skipping LLM cycle")
        response = ""
    else:
        cfg = OpenSpaceConfig(llm_model=MODEL)
        start = time.time()
        try:
            async with OpenSpace(config=cfg) as cs:
                result = await cs.execute(prompt)
            elapsed = time.time() - start
            response = result.get("response") or result.get("output") or ""
            log.info("meta_llm_response chars=%d elapsed=%.1fs", len(response), elapsed)
        except Exception as e:
            log.exception("meta_llm_failed")
            response = ""

    # ── Step 7: Parse and execute LLM output ─────────────────────────────────
    # Parse <<<SPAWN>>> blocks
    spawn_resp = response
    while "<<<SPAWN>>>" in spawn_resp and "<<<END_SPAWN>>>" in spawn_resp:
        raw = spawn_resp.split("<<<SPAWN>>>", 1)[1].split("<<<END_SPAWN>>>", 1)[0].strip()
        spawn_resp = spawn_resp.split("<<<END_SPAWN>>>", 1)[1]
        try:
            spawn_req = json.loads(raw)
            api("post", "/agents/spawn", json={**spawn_req, "created_by": "meta"})
            state["total_agents_spawned"] += 1
            log.info("meta_spawn_executed type=%s", spawn_req.get("type"))
        except Exception as e:
            log.error("meta_spawn_parse_failed error=%s raw=%r", e, raw[:200])

    # Parse <<<KILL>>> blocks
    kill_resp = response
    while "<<<KILL>>>" in kill_resp and "<<<END_KILL>>>" in kill_resp:
        raw = kill_resp.split("<<<KILL>>>", 1)[1].split("<<<END_KILL>>>", 1)[0].strip()
        kill_resp = kill_resp.split("<<<END_KILL>>>", 1)[1]
        try:
            kill_req = json.loads(raw)
            api("post", f"/agents/{kill_req['agent_id']}/kill",
                params={"reason": kill_req.get("reason", "meta_directive")})
            state["total_agents_killed"] += 1
            log.info("meta_kill_executed agent=%s", kill_req.get("agent_id"))
        except Exception as e:
            log.error("meta_kill_parse_failed error=%s", e)

    # Parse <<<TASK>>> blocks
    task_resp = response
    while "<<<TASK>>>" in task_resp and "<<<END_TASK>>>" in task_resp:
        raw = task_resp.split("<<<TASK>>>", 1)[1].split("<<<END_TASK>>>", 1)[0].strip()
        task_resp = task_resp.split("<<<END_TASK>>>", 1)[1]
        try:
            task_req = json.loads(raw)
            if "inputs" not in task_req:
                task_req["inputs"] = {}
            api("post", "/tasks", json=task_req)
            log.info("meta_task_proposed title=%r", task_req.get("title", "")[:60])
        except Exception as e:
            log.error("meta_task_parse_failed error=%s raw=%r", e, raw[:200])

    # ── Step 8: Daily digest ──────────────────────────────────────────────────
    if in_digest_window(now):
        today_ist = (now + timedelta(hours=5, minutes=30)).date().isoformat()
        if state.get("last_digest_date_ist") != today_ist:
            if "<<<TG_DIGEST>>>" in response and "<<<END_TG_DIGEST>>>" in response:
                msg = response.split("<<<TG_DIGEST>>>", 1)[1].split("<<<END_TG_DIGEST>>>", 1)[0].strip()
                if msg:
                    send_telegram(msg)
                    state["last_digest_date_ist"] = today_ist
                    log.info("daily_digest_sent date=%s", today_ist)

    state["cycle_number"] = cycle
    state["last_cycle_at_utc"] = now.isoformat()
    log.info("meta_cycle_complete cycle=%d spawned=%d killed=%d",
             cycle, len(spawned_this_cycle), len(cull_candidates))
    return state


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    log.info("meta_agent_starting interval_hours=%.1f model=%s", INTERVAL_HOURS, MODEL)
    state = load_state()

    while True:
        try:
            state = await run_meta_cycle(state)
            save_state(state)
        except Exception:
            log.exception("meta_cycle_crashed will_retry")

        sleep_s = INTERVAL_HOURS * 3600
        log.info("meta_sleeping %.0fs", sleep_s)
        await asyncio.sleep(sleep_s)


if __name__ == "__main__":
    asyncio.run(main())

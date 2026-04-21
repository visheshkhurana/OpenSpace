"""
Cleya Control Tower — FastAPI Orchestrator
==========================================
The single brain that all services talk to.
Every mutation goes through here; Supabase is never written directly from UI.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Optional, List
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from supabase import create_client, Client

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
log = logging.getLogger("control-tower-api")

# ── Config ───────────────────────────────────────────────────────────────────
CONTROL_TOWER_TOKEN  = os.environ["CONTROL_TOWER_TOKEN"]
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
TELEGRAM_BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN")
HUMAN_CHAT_ID        = int(os.environ.get("HUMAN_CHAT_ID", "6224744296"))
GLOBAL_PAUSE         = os.environ.get("GLOBAL_PAUSE", "0") == "1"
FOUNDER_MODE         = os.environ.get("FOUNDER_MODE", "AUTO")

# ── Supabase Client ──────────────────────────────────────────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Cleya Control Tower API",
    version="2.0.0",
    description="Orchestrator for the self-evolving AI company",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ─────────────────────────────────────────────────────────────────────
security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != CONTROL_TOWER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


# ── Telegram helper ──────────────────────────────────────────────────────────
import urllib.request as _urllib_req


def send_telegram(text: str, reply_markup: dict = None) -> dict:
    """Send message to HUMAN_CHAT_ID; returns Telegram API response."""
    if not TELEGRAM_BOT_TOKEN:
        return {}
    payload = {
        "chat_id": HUMAN_CHAT_ID,
        "text": text[:4000],
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = json.dumps(payload).encode()
    req = _urllib_req.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with _urllib_req.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error("telegram_send_failed error=%s", e)
        return {}


def audit(agent_id: str, event: str, payload: dict = None, worker_id: str = None):
    """Write one row to agent_audit_log (fire-and-forget)."""
    try:
        supabase.table("agent_audit_log").insert({
            "agent_id": agent_id,
            "event": event,
            "payload": payload or {},
            "worker_id": worker_id,
        }).execute()
    except Exception as e:
        log.error("audit_write_failed agent=%s event=%s error=%s", agent_id, event, e)


def get_founder_mode() -> str:
    """Get current FOUNDER_MODE from DB or env."""
    env_mode = os.environ.get("FOUNDER_MODE", "AUTO").upper()
    if env_mode in ("AUTO", "REVIEW", "MANUAL"):
        return env_mode
    try:
        result = supabase.table("founder_mode_config").select("mode").order("set_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]["mode"]
    except Exception:
        pass
    return "AUTO"


def queue_approval(action: str, payload: dict, risk: str = "MEDIUM") -> str:
    """Store a pending approval in approvals_inbox. Returns a stub ID."""
    return f"approval_pending_{action}"


async def build_inherited_context(ctx) -> str:
    """Async inherited context builder."""
    if not ctx or not ctx.from_agent_ids:
        return ""
    from_ids = ctx.from_agent_ids
    try:
        tasks = (
            supabase.table("tasks")
            .select("title, outputs, completed_at")
            .in_("agent_id", from_ids)
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(5)
            .execute()
            .data
        )
        lines = []
        for t in tasks or []:
            outputs = t.get("outputs") or {}
            summary = outputs.get("summary", "")
            lines.append(f"- {t['title']}: {summary[:150]}")
        return "\n".join(lines)
    except Exception:
        return ""


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class SpawnAgentRequest(BaseModel):
    parent_id: Optional[str] = None
    type: str = Field(..., description="e.g. 'growth-micro', 'sales', 'product'")
    goal: str = Field(..., min_length=10)
    skill_ref: str = Field(..., description="Path under host_skills/, e.g. 'cleya-growth'")
    level: int = Field(..., ge=1, le=3)
    created_by: str = Field(default="meta")
    metadata: dict = Field(default_factory=dict)


class ProposeTaskRequest(BaseModel):
    agent_id: str
    title: str = Field(..., min_length=5)
    inputs: dict = Field(default_factory=dict)
    proposed_action: str = Field(..., min_length=10)
    risk_level: str = Field(default="LOW", pattern="^(LOW|MEDIUM|HIGH)$")
    revenue_impact_score: int = Field(..., ge=3, le=10)
    urgency: int = Field(default=5, ge=1, le=10)
    confidence: int = Field(default=5, ge=1, le=10)


class MetaTickRequest(BaseModel):
    cycle_number: int
    current_metrics: dict = Field(default_factory=dict)
    notes: str = Field(default="")


class ApprovalCallbackRequest(BaseModel):
    callback_data: str
    from_user_id: int
    telegram_message_id: Optional[int] = None


class IngestMetricsRequest(BaseModel):
    key: str
    value: float
    source: str = Field(default="manual")
    metadata: dict = Field(default_factory=dict)


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    prompt_fragment: str
    tools: List[str] = []
    cost_profile: dict = {}
    default_risk: str = "LOW"


class ContextInheritance(BaseModel):
    from_agent_ids: List[str] = []
    memory_ids: List[str] = []
    include_task_outcomes: bool = True
    max_tokens: int = 2000


class ComposeRequest(BaseModel):
    required_skills: List[str]
    goal: str
    context_inheritance: ContextInheritance = Field(default_factory=ContextInheritance)
    level: int = 3


class Mutation(BaseModel):
    skill_name: str
    prompt_overlay: str


class CloneRequest(BaseModel):
    n: int
    mutations: List[Mutation] = []


class EvolveRequest(BaseModel):
    reason: str


class CreateTournamentRequest(BaseModel):
    task_id: Optional[str] = None
    contestants: List[str]
    judge_criteria: dict = Field(default_factory=lambda: {"quality": 0.5, "cost": 0.3, "speed": 0.2})
    time_box_hours: int = 48


class CreateJobRequest(BaseModel):
    task_requirements: dict


class ApplyRequest(BaseModel):
    agent_id: str
    pitch: str
    estimated_cost_tokens: int = 0
    estimated_quality: float = 0.0


class SelectRequest(BaseModel):
    agent_id: str


class CreateTeamRequest(BaseModel):
    name: str
    purpose: str
    lead_agent_id: str
    members: List[str] = []


class CreateMemoryRequest(BaseModel):
    agent_id: str
    key: str
    value: object
    relevance_decay_days: int = 30
    pinned: bool = False


class ModeSetRequest(BaseModel):
    mode: str = Field(..., pattern="^(AUTO|REVIEW|MANUAL)$")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/healthz", tags=["system"])
async def healthz():
    """Render health check endpoint."""
    try:
        supabase.table("agents").select("id").limit(1).execute()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "global_pause": GLOBAL_PAUSE,
        "founder_mode": get_founder_mode(),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


# ── Agent Endpoints ───────────────────────────────────────────────────────────

@app.post("/agents/spawn", tags=["agents"])
async def spawn_agent(req: SpawnAgentRequest, token: str = Depends(verify_token)):
    if GLOBAL_PAUSE:
        raise HTTPException(503, detail="GLOBAL_PAUSE=1 — all execution halted")

    if req.level == 2:
        res = supabase.table("agents").select("id").eq("level", 2).eq("status", "active").execute()
        if len(res.data) >= 3:
            raise HTTPException(409, detail="Level-2 agent cap reached (max 3 active).")
    elif req.level == 3:
        res = supabase.table("agents").select("id").eq("level", 3).eq("status", "active").execute()
        if len(res.data) >= 5:
            raise HTTPException(409, detail="Level-3 agent cap reached (max 5 active).")

    agent_row = {
        "level": req.level,
        "parent_id": req.parent_id,
        "type": req.type,
        "status": "active",
        "skill_ref": req.skill_ref,
        "goal": req.goal,
        "created_by": req.created_by,
        "metadata": req.metadata,
        "founder_mode": get_founder_mode(),
    }
    result = supabase.table("agents").insert(agent_row).execute()
    agent = result.data[0]
    agent_id = agent["id"]

    bootstrap_task = {
        "agent_id": agent_id,
        "title": f"Bootstrap: {req.goal[:80]}",
        "inputs": {"goal": req.goal, "skill_ref": req.skill_ref},
        "proposed_action": f"Initialize agent and begin working toward goal: {req.goal}",
        "risk_level": "LOW",
        "revenue_impact_score": 5,
        "urgency": 5,
        "confidence": 7,
        "status": "queued",
    }
    task_res = supabase.table("tasks").insert(bootstrap_task).execute()
    task_id = task_res.data[0]["id"]

    audit(agent_id, "spawned", {"goal": req.goal, "skill_ref": req.skill_ref, "bootstrap_task_id": task_id})
    log.info("agent_spawned id=%s type=%s level=%d", agent_id, req.type, req.level)
    return {"agent_id": agent_id, "status": "active", "bootstrap_task_id": task_id}


@app.post("/agents/{agent_id}/kill", tags=["agents"])
async def kill_agent(agent_id: str, reason: str = "user_directive", token: str = Depends(verify_token)):
    supabase.table("agents").update({
        "status": "killed",
        "killed_at": datetime.now(timezone.utc).isoformat(),
        "kill_reason": reason,
    }).eq("id", agent_id).execute()

    cancelled = supabase.table("tasks").update({
        "status": "rejected",
        "error_message": f"Agent killed: {reason}",
    }).eq("agent_id", agent_id).in_("status", ["queued", "awaiting_approval"]).execute()

    tasks_cancelled = len(cancelled.data) if cancelled.data else 0
    audit(agent_id, "killed", {"reason": reason, "tasks_cancelled": tasks_cancelled})
    return {"agent_id": agent_id, "status": "killed", "tasks_cancelled": tasks_cancelled}


@app.get("/agents", tags=["agents"])
async def list_agents(
    level: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    token: str = Depends(verify_token),
):
    q = supabase.table("agents").select(
        "id, level, type, status, skill_ref, goal, spawned_at, killed_at, "
        "kill_reason, revenue_contrib_inr, tasks_done, success_rate, created_by, metadata"
    ).order("spawned_at", desc=True).limit(limit)

    if level is not None:
        q = q.eq("level", level)
    if status:
        q = q.eq("status", status)

    result = q.execute()
    return {"agents": result.data, "total": len(result.data)}


@app.get("/agents/{agent_id}", tags=["agents"])
async def get_agent(agent_id: str, token: str = Depends(verify_token)):
    agent_res = supabase.table("agents").select("*").eq("id", agent_id).single().execute()
    if not agent_res.data:
        raise HTTPException(404, detail="Agent not found")

    tasks_res = supabase.table("tasks").select("*").eq("agent_id", agent_id).order("queued_at", desc=True).limit(20).execute()
    audit_res = supabase.table("agent_audit_log").select("*").eq("agent_id", agent_id).order("ts", desc=True).limit(50).execute()

    return {
        "agent": agent_res.data,
        "recent_tasks": tasks_res.data,
        "recent_audit": audit_res.data,
    }


@app.post("/agents/compose", tags=["agents"])
async def compose_agent(req: ComposeRequest, token: str = Depends(verify_token)):
    if os.getenv("GLOBAL_PAUSE", "0") == "1":
        raise HTTPException(503, "GLOBAL_PAUSE active")

    skills = supabase.table("skill_library").select("*").in_("name", req.required_skills).execute().data
    if len(skills) != len(req.required_skills):
        found = {s["name"] for s in skills}
        missing = set(req.required_skills) - found
        raise HTTPException(422, f"Skills not in library: {missing}")

    mode = get_founder_mode()
    if mode == "MANUAL":
        raise HTTPException(202, "Queued for MANUAL approval")

    combined_prompt = "\n\n---\n\n".join(s["prompt_fragment"] for s in skills)
    composite_skill_ref = "composed/" + "+".join(sorted(req.required_skills))

    agent_row = {
        "level": req.level,
        "type": "composed",
        "status": "active",
        "skill_ref": composite_skill_ref,
        "goal": req.goal,
        "created_by": "compose-endpoint",
        "metadata": {"required_skills": req.required_skills, "prompt_fragment": combined_prompt[:500]},
    }
    agent = supabase.table("agents").insert(agent_row).execute().data[0]
    agent_id = agent["id"]

    skill_links = [{"agent_id": agent_id, "skill_id": s["id"]} for s in skills]
    supabase.table("agent_skills").insert(skill_links).execute()

    inherited_context = await build_inherited_context(req.context_inheritance)
    task_row = {
        "agent_id": agent_id,
        "title": f"[COMPOSED] {req.goal[:80]}",
        "inputs": {"inherited_context": inherited_context},
        "proposed_action": req.goal,
        "risk_level": max((s["default_risk"] for s in skills), key=lambda x: ["LOW","MEDIUM","HIGH"].index(x)),
        "revenue_impact_score": 5,
        "status": "queued",
    }
    task = supabase.table("tasks").insert(task_row).execute().data[0]
    audit(agent_id, "agent_composed", {"skills": req.required_skills})
    return {"agent_id": agent_id, "task_id": task["id"]}


@app.post("/agents/{agent_id}/clone", tags=["agents"])
async def clone_agent(agent_id: str, req: CloneRequest, token: str = Depends(verify_token)):
    if req.n < 1 or req.n > 5:
        raise HTTPException(422, "n must be 1–5")

    parent = supabase.table("agents").select("*").eq("id", agent_id).single().execute().data
    if not parent:
        raise HTTPException(404, "Agent not found")

    mutation_map = {m.skill_name: m.prompt_overlay for m in req.mutations}
    child_ids = []

    for i in range(req.n):
        child_row = {
            "level": parent["level"],
            "type": parent["type"],
            "status": "pending",
            "skill_ref": parent["skill_ref"],
            "goal": parent["goal"],
            "created_by": "clone-orchestrator",
            "metadata": {
                **parent.get("metadata", {}),
                "clone_index": i,
                "parent_id": agent_id,
                "mutation_map": mutation_map,
            },
        }
        child = supabase.table("agents").insert(child_row).execute().data[0]
        child_ids.append(child["id"])

    contestants = [agent_id] + child_ids
    t_row = {"status": "open", "judge_criteria": {"quality": 0.5, "cost": 0.3, "speed": 0.2}, "time_box_hours": req.n * 24}
    tournament = supabase.table("tournaments").insert(t_row).execute().data[0]
    tournament_id = tournament["id"]

    entries = [{"tournament_id": tournament_id, "agent_id": cid} for cid in contestants]
    supabase.table("tournament_entries").insert(entries).execute()

    audit(agent_id, "agents_cloned", {"child_ids": child_ids, "tournament_id": tournament_id})
    return {"child_agent_ids": child_ids, "tournament_id": tournament_id}


@app.post("/agents/{agent_id}/evolve", tags=["agents"])
async def queue_evolution(agent_id: str, req: EvolveRequest, token: str = Depends(verify_token)):
    agent = supabase.table("agents").select("version").eq("id", agent_id).single().execute().data
    if not agent:
        raise HTTPException(404, "Agent not found")

    evo_row = {
        "agent_id": agent_id,
        "from_version": agent.get("version", 1),
        "to_version": agent.get("version", 1) + 1,
        "change_summary": "pending — evolution runner will populate",
        "reason": req.reason,
        "status": "pending",
    }
    evo = supabase.table("agent_evolutions").insert(evo_row).execute().data[0]
    audit(agent_id, "evolution_queued", {"evolution_id": evo["id"]})
    return {"evolution_id": evo["id"]}


# ── Task Endpoints ────────────────────────────────────────────────────────────

@app.post("/tasks", tags=["tasks"])
async def propose_task(req: ProposeTaskRequest, token: str = Depends(verify_token)):
    if GLOBAL_PAUSE:
        raise HTTPException(503, detail="GLOBAL_PAUSE=1 — all execution halted")

    agent_res = supabase.table("agents").select("id, type, level, goal").eq("id", req.agent_id).eq("status", "active").single().execute()
    if not agent_res.data:
        raise HTTPException(404, detail="Agent not found or not active")

    mode = get_founder_mode()
    if mode == "REVIEW" and req.risk_level == "LOW":
        req.risk_level = "MEDIUM"

    initial_status = "queued"
    approval_required = False

    if req.risk_level == "HIGH":
        initial_status = "awaiting_approval"
        approval_required = True

    task_row = {
        "agent_id": req.agent_id,
        "title": req.title,
        "inputs": req.inputs,
        "proposed_action": req.proposed_action,
        "risk_level": req.risk_level,
        "revenue_impact_score": req.revenue_impact_score,
        "urgency": req.urgency,
        "confidence": req.confidence,
        "status": initial_status,
    }

    result = supabase.table("tasks").insert(task_row).execute()
    task = result.data[0]
    task_id = task["id"]

    audit(req.agent_id, "task_queued", {"task_id": task_id, "title": req.title, "risk_level": req.risk_level})

    if req.risk_level == "HIGH":
        supabase.table("approvals_inbox").insert({"task_id": task_id, "risk": "HIGH"}).execute()
        agent = agent_res.data
        tg_text = (
            f"🚨 *HIGH-RISK TASK — APPROVAL REQUIRED*\n\n"
            f"Agent: `{agent['type']}` (Level {agent['level']})\n"
            f"Goal: {agent['goal'][:100]}\n\n"
            f"*Task:* {req.title}\n"
            f"*Action:* {req.proposed_action[:300]}\n\n"
            f"Revenue Impact: {req.revenue_impact_score}/10 | "
            f"Urgency: {req.urgency}/10 | "
            f"Confidence: {req.confidence}/10\n\n"
            f"Task ID: `{task_id}`"
        )
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ APPROVE", "callback_data": f"approve:{task_id}"},
                {"text": "❌ DENY",    "callback_data": f"deny:{task_id}"},
            ]]
        }
        tg_res = send_telegram(tg_text, reply_markup)
        if tg_res.get("ok") and tg_res.get("result"):
            supabase.table("approvals_inbox").update({"telegram_msg_id": tg_res["result"]["message_id"]}).eq("task_id", task_id).execute()

    elif req.risk_level == "MEDIUM" and mode == "AUTO":
        # Notify but auto-approve after 2h
        send_telegram(f"⚠️ *MEDIUM-RISK task queued*\n\n{req.title}\n\nWill auto-approve in 2h. Tap DENY to block:\nTask ID: `{task_id}`")

    log.info("task_proposed id=%s agent=%s risk=%s rev=%d", task_id, req.agent_id, req.risk_level, req.revenue_impact_score)
    return {"task_id": task_id, "status": initial_status, "approval_required": approval_required}


@app.get("/tasks", tags=["tasks"])
async def list_tasks(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    token: str = Depends(verify_token),
):
    q = supabase.table("tasks").select("*").order("queued_at", desc=True).limit(limit)
    if agent_id:
        q = q.eq("agent_id", agent_id)
    if status:
        q = q.eq("status", status)
    return {"tasks": q.execute().data}


@app.get("/tasks/{task_id}", tags=["tasks"])
async def get_task(task_id: str, token: str = Depends(verify_token)):
    result = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Task not found")
    return result.data


@app.post("/tasks/{task_id}/execute", tags=["tasks"])
async def execute_task(task_id: str, token: str = Depends(verify_token)):
    task_res = supabase.table("tasks").select("id, status, agent_id").eq("id", task_id).single().execute()
    if not task_res.data:
        raise HTTPException(404, detail="Task not found")

    task = task_res.data
    if task["status"] not in ("approved", "queued"):
        raise HTTPException(400, detail=f"Task status is '{task['status']}', cannot execute")

    supabase.table("tasks").update({"status": "queued"}).eq("id", task_id).execute()
    audit(task["agent_id"], "task_execute_triggered", {"task_id": task_id})
    return {"task_id": task_id, "status": "queued"}


@app.post("/tasks/{task_id}/approve", tags=["tasks"])
async def approve_task(task_id: str, approved_by: str = "human", token: str = Depends(verify_token)):
    supabase.table("tasks").update({
        "status": "queued",
        "approval_state": "approved",
        "approved_by": approved_by,
    }).eq("id", task_id).execute()

    supabase.table("approvals_inbox").update({
        "decision": "approved",
        "decided_by": approved_by,
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }).eq("task_id", task_id).execute()

    task_res = supabase.table("tasks").select("agent_id").eq("id", task_id).single().execute()
    if task_res.data:
        audit(task_res.data["agent_id"], "approval_received", {"task_id": task_id, "decision": "approved", "by": approved_by})

    return {"task_id": task_id, "status": "queued"}


@app.post("/tasks/{task_id}/deny", tags=["tasks"])
async def deny_task(task_id: str, denied_by: str = "human", token: str = Depends(verify_token)):
    supabase.table("tasks").update({
        "status": "denied",
        "approval_state": "denied",
        "approved_by": denied_by,
    }).eq("id", task_id).execute()

    supabase.table("approvals_inbox").update({
        "decision": "denied",
        "decided_by": denied_by,
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }).eq("task_id", task_id).execute()

    task_res = supabase.table("tasks").select("agent_id").eq("id", task_id).single().execute()
    if task_res.data:
        audit(task_res.data["agent_id"], "approval_received", {"task_id": task_id, "decision": "denied", "by": denied_by})

    return {"task_id": task_id, "status": "denied"}


# ── Metrics Endpoints ─────────────────────────────────────────────────────────

@app.get("/metrics", tags=["metrics"])
async def get_metrics(key: Optional[str] = None, limit: int = 100, token: str = Depends(verify_token)):
    if key:
        result = supabase.table("metrics").select("*").eq("key", key).order("ts", desc=True).limit(limit).execute()
    else:
        result = supabase.table("v_latest_metrics").select("*").execute()
        if not result.data:
            result = supabase.table("metrics").select("*").order("ts", desc=True).limit(limit).execute()
    return {"metrics": result.data}


@app.post("/metrics/ingest", tags=["metrics"])
async def ingest_metric(req: IngestMetricsRequest, token: str = Depends(verify_token)):
    result = supabase.table("metrics").insert({
        "key": req.key,
        "value": req.value,
        "source": req.source,
        "metadata": req.metadata,
    }).execute()
    return {"id": result.data[0]["id"], "ts": result.data[0]["ts"]}


# ── Feed / SSE ────────────────────────────────────────────────────────────────

@app.get("/feed", tags=["ui"])
async def activity_feed(request: Request, token: Optional[str] = None):
    """Server-Sent Events stream of agent_audit_log events. Token via query param."""
    # EventSource can't send Authorization header, accept token as query param
    expected = os.environ["CONTROL_TOWER_TOKEN"]
    if token != expected:
        raise HTTPException(401, "Unauthorized")
    async def event_generator() -> AsyncGenerator[str, None]:
        last_id = 0
        res = supabase.table("agent_audit_log").select("id").order("id", desc=True).limit(1).execute()
        if res.data:
            last_id = res.data[0]["id"]

        while True:
            if await request.is_disconnected():
                break
            try:
                new_rows = supabase.table("agent_audit_log")\
                    .select("id, agent_id, event, payload, ts")\
                    .gt("id", last_id)\
                    .order("id", desc=False)\
                    .limit(20)\
                    .execute()

                for row in (new_rows.data or []):
                    last_id = row["id"]
                    yield {"event": "audit", "data": json.dumps(row), "id": str(row["id"])}
            except Exception as e:
                log.error("feed_error: %s", e)
                yield {"event": "error", "data": json.dumps({"error": str(e)})}

            await asyncio.sleep(3)

    return EventSourceResponse(event_generator())


# ── Meta Tick ─────────────────────────────────────────────────────────────────

@app.post("/meta/tick", tags=["meta"])
async def meta_tick(req: MetaTickRequest, token: str = Depends(verify_token)):
    if GLOBAL_PAUSE:
        return {"cycle_number": req.cycle_number, "system_status": "paused",
                "metrics": {}, "active_agents": [], "pending_approvals": [], "triggered_rules": []}

    metrics_res = supabase.table("metrics").select("key, value, ts").order("ts", desc=True).limit(100).execute()
    metrics_dict = {}
    for m in (metrics_res.data or []):
        if m["key"] not in metrics_dict:
            metrics_dict[m["key"]] = m["value"]

    agents_res = supabase.table("agents")\
        .select("id, level, type, status, goal, tasks_done, success_rate, revenue_contrib_inr")\
        .eq("status", "active").execute()

    approvals_res = supabase.table("approvals_inbox").select("task_id, sent_at, risk").is_("decision", "null").execute()

    rules_res = supabase.table("spawn_rules").select("*").eq("enabled", True).execute()
    now = datetime.now(timezone.utc)
    triggered_rules = []
    for rule in (rules_res.data or []):
        metric_val = metrics_dict.get(rule["trigger_metric"])
        if metric_val is None:
            continue
        op = rule["operator"]
        threshold = float(rule["threshold"])
        val = float(metric_val)
        triggered = (
            (op == "<"  and val <  threshold) or
            (op == "<=" and val <= threshold) or
            (op == ">"  and val >  threshold) or
            (op == ">=" and val >= threshold) or
            (op == "="  and val == threshold)
        )
        if triggered:
            if rule.get("last_fired_at"):
                try:
                    last_fired = datetime.fromisoformat(rule["last_fired_at"].replace("Z", "+00:00"))
                    elapsed_h = (now - last_fired).total_seconds() / 3600
                    if elapsed_h < rule["cooldown_hours"]:
                        continue
                except Exception:
                    pass
            triggered_rules.append({
                "rule_id": rule["id"],
                "name": rule["name"],
                "metric": rule["trigger_metric"],
                "current_value": val,
                "threshold": threshold,
                "agent_type_to_spawn": rule["agent_type_to_spawn"],
                "goal_template": rule["goal_template"],
            })

    return {
        "cycle_number": req.cycle_number,
        "system_status": "ok",
        "metrics": metrics_dict,
        "active_agents": agents_res.data or [],
        "pending_approvals": approvals_res.data or [],
        "triggered_rules": triggered_rules,
    }


# ── Telegram Webhook ──────────────────────────────────────────────────────────

@app.post("/telegram/webhook", tags=["telegram"])
async def telegram_webhook(request: Request):
    """Receives Telegram callback_query events. No bearer auth required."""
    body = await request.json()
    callback_data = body.get("callback_data", "")
    from_user = body.get("from_user_id", 0)

    if not callback_data or ":" not in callback_data:
        return {"ok": False, "reason": "invalid callback_data"}

    action, task_id = callback_data.split(":", 1)

    if from_user != HUMAN_CHAT_ID:
        log.warning("telegram_webhook unauthorized user=%d", from_user)
        return {"ok": False, "reason": "not authorized"}

    if action == "approve":
        await approve_task(task_id, approved_by=f"human:{from_user}", token=CONTROL_TOWER_TOKEN)
        send_telegram(f"✅ Task `{task_id[:8]}...` *approved* and queued for execution.")
    elif action == "deny":
        await deny_task(task_id, denied_by=f"human:{from_user}", token=CONTROL_TOWER_TOKEN)
        send_telegram(f"❌ Task `{task_id[:8]}...` *denied*.")
    else:
        return {"ok": False, "reason": f"unknown action: {action}"}

    return {"ok": True, "action": action, "task_id": task_id}


# ── Skills Library ────────────────────────────────────────────────────────────

@app.post("/skills/library", tags=["skills"], status_code=201)
async def create_skill(req: SkillCreateRequest, token: str = Depends(verify_token)):
    row = {
        "name": req.name,
        "description": req.description,
        "prompt_fragment": req.prompt_fragment,
        "tools": req.tools,
        "cost_profile": req.cost_profile,
        "default_risk": req.default_risk,
    }
    result = supabase.table("skill_library").insert(row).execute()
    return result.data[0]


@app.get("/skills/library", tags=["skills"])
async def list_skills(risk: Optional[str] = None, token: str = Depends(verify_token)):
    q = supabase.table("skill_library").select("*").order("times_used", desc=True)
    if risk:
        q = q.eq("default_risk", risk)
    return q.execute().data


# ── Tournament Endpoints ──────────────────────────────────────────────────────

@app.post("/tournaments", tags=["tournaments"], status_code=201)
async def create_tournament(req: CreateTournamentRequest, token: str = Depends(verify_token)):
    t_row = {"task_id": req.task_id, "status": "open", "judge_criteria": req.judge_criteria, "time_box_hours": req.time_box_hours}
    t = supabase.table("tournaments").insert(t_row).execute().data[0]
    entries = [{"tournament_id": t["id"], "agent_id": aid} for aid in req.contestants]
    supabase.table("tournament_entries").insert(entries).execute()
    return {"tournament_id": t["id"], "status": "open"}


@app.get("/tournaments/{tournament_id}", tags=["tournaments"])
async def get_tournament(tournament_id: str, token: str = Depends(verify_token)):
    t = supabase.table("tournaments").select("*").eq("id", tournament_id).single().execute().data
    if not t:
        raise HTTPException(404, "Tournament not found")
    entries = supabase.table("tournament_entries").select("*").eq("tournament_id", tournament_id).execute().data
    return {**t, "entries": entries}


@app.post("/tournaments/{tournament_id}/resolve", tags=["tournaments"])
async def resolve_tournament(tournament_id: str, token: str = Depends(verify_token)):
    """Trigger tournament resolution via the judge agent."""
    t = supabase.table("tournaments").select("*").eq("id", tournament_id).single().execute().data
    if not t:
        raise HTTPException(404, "Tournament not found")
    supabase.table("tournaments").update({"status": "judging"}).eq("id", tournament_id).execute()
    return {"tournament_id": tournament_id, "status": "judging", "message": "Judge task queued"}


# ── Job Marketplace ────────────────────────────────────────────────────────────

@app.post("/jobs", tags=["jobs"], status_code=201)
async def post_job(req: CreateJobRequest, token: str = Depends(verify_token)):
    closes = datetime.now(timezone.utc) + timedelta(minutes=30)
    row = {"requirements": req.task_requirements, "status": "open", "closes_at": closes.isoformat()}
    job = supabase.table("job_posts").insert(row).execute().data[0]
    return {"job_id": job["id"], "closes_at": job["closes_at"]}


@app.get("/jobs", tags=["jobs"])
async def list_jobs(status: Optional[str] = None, token: str = Depends(verify_token)):
    q = supabase.table("job_posts").select("*").order("posted_at", desc=True)
    if status:
        q = q.eq("status", status)
    return q.execute().data


@app.post("/jobs/{job_id}/apply", tags=["jobs"], status_code=201)
async def apply_to_job(job_id: str, req: ApplyRequest, token: str = Depends(verify_token)):
    job = supabase.table("job_posts").select("status").eq("id", job_id).single().execute().data
    if not job or job["status"] != "open":
        raise HTTPException(422, "Job not open for applications")
    row = {
        "job_post_id": job_id,
        "agent_id": req.agent_id,
        "pitch": req.pitch,
        "estimated_cost_tokens": req.estimated_cost_tokens,
        "estimated_quality": req.estimated_quality,
    }
    supabase.table("applications").upsert(row, on_conflict="job_post_id,agent_id").execute()
    return {"status": "applied"}


@app.post("/jobs/{job_id}/select", tags=["jobs"])
async def select_job_winner(job_id: str, req: SelectRequest, token: str = Depends(verify_token)):
    supabase.table("job_posts").update({"status": "filled", "selected_agent_id": req.agent_id}).eq("id", job_id).execute()
    return {"status": "filled", "selected_agent_id": req.agent_id}


# ── Teams ─────────────────────────────────────────────────────────────────────

@app.post("/teams", tags=["teams"], status_code=201)
async def create_team(req: CreateTeamRequest, token: str = Depends(verify_token)):
    row = {"name": req.name, "purpose": req.purpose, "lead_agent_id": req.lead_agent_id}
    team = supabase.table("teams").insert(row).execute().data[0]
    all_members = list(set([req.lead_agent_id] + req.members))
    for agent_id in all_members:
        supabase.table("agents").update({"team_id": team["id"]}).eq("id", agent_id).execute()
    return team


@app.post("/teams/{team_id}/disband", tags=["teams"])
async def disband_team(team_id: str, token: str = Depends(verify_token)):
    supabase.table("teams").update({"disbanded_at": datetime.now(timezone.utc).isoformat()}).eq("id", team_id).execute()
    supabase.table("agents").update({"team_id": None}).eq("team_id", team_id).execute()
    return {"status": "disbanded"}


# ── Memories ──────────────────────────────────────────────────────────────────

@app.post("/memories", tags=["memories"], status_code=201)
async def create_memory(req: CreateMemoryRequest, token: str = Depends(verify_token)):
    value = req.value if isinstance(req.value, dict) else {"data": req.value}
    row = {
        "agent_id": req.agent_id,
        "key": req.key,
        "value": value,
        "relevance_decay_days": req.relevance_decay_days,
        "pinned": req.pinned,
    }
    mem = supabase.table("memories").insert(row).execute().data[0]
    return mem


@app.get("/memories", tags=["memories"])
async def list_memories(
    agent_id: Optional[str] = None,
    key: Optional[str] = None,
    pinned: Optional[bool] = None,
    token: str = Depends(verify_token),
):
    q = supabase.table("memories").select("*").order("last_used_at", desc=True)
    if agent_id:
        q = q.eq("agent_id", agent_id)
    if key:
        q = q.eq("key", key)
    if pinned is not None:
        q = q.eq("pinned", pinned)
    return q.execute().data


# ── Mode Endpoint ─────────────────────────────────────────────────────────────

@app.get("/mode", tags=["mode"])
async def get_mode(token: str = Depends(verify_token)):
    return {"mode": get_founder_mode()}


@app.post("/mode", tags=["mode"])
async def set_mode(req: ModeSetRequest, token: str = Depends(verify_token)):
    try:
        supabase.table("founder_mode_config").insert({"mode": req.mode, "set_by": "api"}).execute()
        os.environ["FOUNDER_MODE"] = req.mode
    except Exception as e:
        raise HTTPException(500, f"Failed to set mode: {e}")
    return {"mode": req.mode}


# ── UI Compatibility Endpoints ────────────────────────────────────────────────

@app.get("/metrics/overview", tags=["metrics"])
async def metrics_overview(token: str = Depends(verify_token)):
    """Dashboard hero row: MRR, leads, conv rate, active agents."""
    try:
        agents = supabase.table("agents").select("id,status,revenue_contrib_inr,tasks_done").execute().data or []
        active = [a for a in agents if a.get("status") == "active"]
        total_revenue = sum(float(a.get("revenue_contrib_inr") or 0) for a in agents)
        total_tasks = sum(int(a.get("tasks_done") or 0) for a in agents)
        return {
            "mrr_inr": total_revenue,
            "mrr_target_inr": 4_150_000,
            "mrr_delta_wow": 0,
            "leads_today": 0,
            "leads_7d_avg": 0,
            "conv_rate_pct": 0.0,
            "conv_rate_delta_pp": 0.0,
            "active_agents": len(active),
            "total_agents": len(agents),
            "tasks_completed_today": total_tasks,
            "cost_inr_today": 0,
            "cost_inr_mtd": 0,
        }
    except Exception as e:
        log.exception("metrics_overview_failed")
        return {"mrr_inr": 0, "mrr_target_inr": 4_150_000, "mrr_delta_wow": 0, "leads_today": 0, "leads_7d_avg": 0, "conv_rate_pct": 0.0, "conv_rate_delta_pp": 0.0, "active_agents": 0, "total_agents": 0}


@app.get("/approvals", tags=["approvals"])
async def list_approvals(token: str = Depends(verify_token)):
    """Pending approvals for the UI carousel."""
    try:
        res = supabase.table("approvals_inbox").select("*").eq("status", "pending").order("created_at", desc=True).limit(50).execute()
        return res.data or []
    except Exception:
        return []


@app.get("/meta/summary", tags=["meta"])
async def meta_summary(token: str = Depends(verify_token)):
    """Latest meta-learning summary for the dashboard card."""
    try:
        proposals = supabase.table("approvals_inbox").select("id", count="exact").eq("status", "pending").execute()
        rules = supabase.table("spawn_rules").select("id", count="exact").execute()
        return {
            "proposals_pending": proposals.count or 0,
            "spawn_rules_proposed_this_week": 0,
            "avg_quality_delta_pct": 0.0,
            "last_proposal_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {"proposals_pending": 0, "spawn_rules_proposed_this_week": 0, "avg_quality_delta_pct": 0.0, "last_proposal_at": datetime.now(timezone.utc).isoformat()}


@app.get("/settings/mode", tags=["mode"])
async def settings_mode_alias(token: str = Depends(verify_token)):
    return {"mode": get_founder_mode()}


@app.get("/skills", tags=["skills"])
async def skills_alias(token: str = Depends(verify_token)):
    res = supabase.table("skill_library").select("*").execute()
    return res.data or []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=2)

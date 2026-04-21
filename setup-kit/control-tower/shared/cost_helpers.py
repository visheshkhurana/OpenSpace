"""
shared/cost_helpers.py
Priority formula, cost tracking, token-to-INR conversion.
"""
import math
import os

# GPT-4o-mini: ~$0.15/1M input tokens. At ₹83/USD = ₹0.012/1K tokens
INR_PER_1K_TOKENS = float(os.environ.get("INR_PER_1K_TOKENS", "0.012"))


def compute_priority(
    revenue_impact: float,
    confidence: float,
    urgency: float,
    cost_per_task_inr: float = 0.0,
) -> float:
    """
    Priority formula from spec:
    priority = revenue_impact * confidence / max(urgency, 1) / log(1 + cost_per_task_inr)
    All inputs 1-10 scale except cost_per_task_inr which is in INR.
    """
    base = (revenue_impact * confidence) / max(urgency, 1)
    if cost_per_task_inr > 0:
        base = base / math.log(1 + cost_per_task_inr)
    return round(base, 4)


def tokens_to_inr(tokens: int) -> float:
    """Convert token count to estimated INR cost."""
    return round((tokens / 1000) * INR_PER_1K_TOKENS, 4)


def update_agent_cost(agent_id: str, tokens_used: int):
    """Add token cost to agent.cost_to_date_inr."""
    cost = tokens_to_inr(tokens_used)
    if cost <= 0:
        return
    try:
        from shared.supabase_client import get_client
        db = get_client()
        agent = db.table("agents").select("cost_to_date_inr").eq("id", agent_id).single().execute().data
        if agent:
            new_cost = float(agent.get("cost_to_date_inr", 0)) + cost
            db.table("agents").update({"cost_to_date_inr": new_cost}).eq("id", agent_id).execute()
    except Exception:
        pass


def check_budget(agent_id: str) -> bool:
    """Return True if agent is within weekly token budget."""
    try:
        from shared.supabase_client import get_client
        db = get_client()
        agent = db.table("agents").select("cost_to_date_inr, token_budget_weekly_inr").eq("id", agent_id).single().execute().data
        if not agent:
            return True
        budget = float(agent.get("token_budget_weekly_inr", 500))
        spent = float(agent.get("cost_to_date_inr", 0))
        return spent < budget
    except Exception:
        return True

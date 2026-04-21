"""
shared/supabase_client.py
Supabase client singleton + helper utilities.
"""
import os
from supabase import create_client, Client

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


# Convenience alias
supabase = get_client()


def audit(agent_id: str, event: str, payload: dict = None, worker_id: str = None):
    """Write one row to agent_audit_log (fire-and-forget)."""
    import logging
    log = logging.getLogger("supabase_client")
    try:
        get_client().table("agent_audit_log").insert({
            "agent_id": agent_id,
            "event": event,
            "payload": payload or {},
            "worker_id": worker_id,
        }).execute()
    except Exception as e:
        log.error("audit_write_failed agent=%s event=%s error=%s", agent_id, event, e)

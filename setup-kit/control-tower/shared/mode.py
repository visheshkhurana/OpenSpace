"""
shared/mode.py
FOUNDER_MODE — read/write with DB-backed persistence.
Valid modes: AUTO, REVIEW, MANUAL
Default: AUTO
"""
import logging
import os

log = logging.getLogger("mode")
_cached_mode: str | None = None


def get_founder_mode() -> str:
    """
    Get current FOUNDER_MODE.
    Priority: env var > DB > default AUTO.
    """
    global _cached_mode
    env_mode = os.environ.get("FOUNDER_MODE", "").upper()
    if env_mode in ("AUTO", "REVIEW", "MANUAL"):
        return env_mode

    if _cached_mode:
        return _cached_mode

    try:
        from shared.supabase_client import get_client
        result = (
            get_client()
            .table("founder_mode_config")
            .select("mode")
            .order("set_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            _cached_mode = result.data[0]["mode"]
            return _cached_mode
    except Exception as e:
        log.warning("founder_mode_db_read_failed error=%s", e)

    return "AUTO"


def set_founder_mode(mode: str, set_by: str = "system") -> str:
    """
    Persist FOUNDER_MODE to DB.
    Returns new mode.
    """
    global _cached_mode
    mode = mode.upper()
    if mode not in ("AUTO", "REVIEW", "MANUAL"):
        raise ValueError(f"Invalid mode: {mode}. Must be AUTO, REVIEW, or MANUAL.")

    try:
        from shared.supabase_client import get_client
        get_client().table("founder_mode_config").insert({
            "mode": mode,
            "set_by": set_by,
        }).execute()
        _cached_mode = mode
        log.info("founder_mode_set mode=%s by=%s", mode, set_by)
    except Exception as e:
        log.error("founder_mode_set_failed error=%s", e)

    return mode

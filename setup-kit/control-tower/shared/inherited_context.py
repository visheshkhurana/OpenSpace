"""
shared/inherited_context.py
Build inherited context for agent composition (§23).
Fetches recent task outcomes + memories from specified agent IDs.
"""
import logging
from typing import Optional

log = logging.getLogger("inherited_context")


async def build_inherited_context(
    from_agent_ids: list,
    memory_ids: list = None,
    include_task_outcomes: bool = True,
    max_tokens: int = 2000,
) -> str:
    """
    Build a context string from previous agents' outcomes.
    Used by /agents/compose to give new agents relevant history.

    Returns a string suitable for injection into an LLM prompt.
    """
    from shared.supabase_client import get_client
    db = get_client()
    sections = []

    if from_agent_ids and include_task_outcomes:
        try:
            tasks = (
                db.table("tasks")
                .select("agent_id, title, outputs, completed_at, revenue_impact_score")
                .in_("agent_id", from_agent_ids)
                .eq("status", "completed")
                .order("completed_at", desc=True)
                .limit(10)
                .execute()
                .data
            )
            if tasks:
                task_lines = []
                for t in tasks:
                    outputs = t.get("outputs") or {}
                    summary = outputs.get("summary", "No summary")
                    task_lines.append(
                        f"- Task: {t['title']}\n"
                        f"  Outcome: {summary[:200]}\n"
                        f"  Revenue Impact: {t['revenue_impact_score']}/10"
                    )
                sections.append("## Previous Task Outcomes\n" + "\n".join(task_lines))
        except Exception as e:
            log.warning("context_task_fetch_failed error=%s", e)

    if memory_ids:
        try:
            memories = (
                db.table("memories")
                .select("key, value")
                .in_("id", memory_ids)
                .execute()
                .data
            )
            if memories:
                mem_lines = [
                    f"- {m['key']}: {str(m['value'])[:200]}"
                    for m in memories
                ]
                sections.append("## Relevant Memories\n" + "\n".join(mem_lines))
        except Exception as e:
            log.warning("context_memory_fetch_failed error=%s", e)

    if not sections:
        return "No inherited context available."

    context = "\n\n".join(sections)
    # Rough token limit: 4 chars per token
    return context[: max_tokens * 4]


def build_inherited_context_sync(
    from_agent_ids: list,
    memory_ids: list = None,
    include_task_outcomes: bool = True,
    max_tokens: int = 2000,
) -> str:
    """Synchronous version for use in non-async contexts."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    build_inherited_context(
                        from_agent_ids, memory_ids,
                        include_task_outcomes, max_tokens
                    )
                )
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(
                build_inherited_context(
                    from_agent_ids, memory_ids,
                    include_task_outcomes, max_tokens
                )
            )
    except Exception as e:
        log.error("inherited_context_sync_failed error=%s", e)
        return "No inherited context available."

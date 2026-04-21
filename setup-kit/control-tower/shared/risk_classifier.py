"""
shared/risk_classifier.py
Two-step risk classifier: whitelist first, LLM fallback second.
Lifted from architecture §8.1 and agents doc Part C §6.
"""
import os
from typing import Optional

# ── Step 1: Whitelist ─────────────────────────────────────────────────────────

LOW_ACTIONS = {
    "analyze", "research", "draft", "summarize", "read", "compute",
    "fetch_url", "write_file", "log", "query_db", "generate_report",
    "send_internal_message",
}

MEDIUM_ACTIONS = {
    "post_draft",
    "outbound_dm_draft",
    "send_internal_email",
    "update_public_page",
    "schedule_post",
}

HIGH_ACTIONS = {
    "send_email",
    "send_dm",
    "publish_post",
    "charge_payment",
    "delete_data",
    "deploy_code",
    "call_external_api_write",
    "send_bulk_communication",
    "send_live_dm",
    "send_live_email",
    "whatsapp_broadcast",
    "push_to_main",
    "open_pr",
}

RISK_CLASSIFIER_PROMPT = """Classify the risk level of this action for the Cleya AI company system.

Action: {action}
Context: {context}

Risk levels:
- LOW: internal analysis, research, drafting, reading, file ops — zero external impact
- MEDIUM: something that could be seen publicly or shared, but reversible
- HIGH: irreversible, involves real money, sends communication to real external humans, deploys code

Reply with exactly one word: LOW, MEDIUM, or HIGH."""


def classify_risk(action_verb: str, context: str = "") -> str:
    """
    Classify risk of an action.
    Step 1: keyword whitelist (deterministic).
    Step 2: LLM fallback if ambiguous.
    """
    verb = action_verb.lower().strip()

    for action in HIGH_ACTIONS:
        if action in verb:
            return "HIGH"
    for action in MEDIUM_ACTIONS:
        if action in verb:
            return "MEDIUM"
    for action in LOW_ACTIONS:
        if action in verb:
            return "LOW"

    # MEDIUM is the conservative default for unknowns
    # Try LLM fallback if available
    try:
        return _llm_classify(action_verb, context)
    except Exception:
        return "MEDIUM"


def _llm_classify(action_verb: str, context: str) -> str:
    """LLM fallback for ambiguous actions."""
    import openai
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = RISK_CLASSIFIER_PROMPT.format(action=action_verb, context=context[:300])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5,
        temperature=0,
    )
    answer = resp.choices[0].message.content.strip().upper()
    if answer in ("LOW", "MEDIUM", "HIGH"):
        return answer
    return "MEDIUM"

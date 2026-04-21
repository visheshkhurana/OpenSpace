"""
shared/telegram_client.py
Telegram bot message sending utilities.
"""
import json
import logging
import os
import urllib.request as _ur

log = logging.getLogger("telegram_client")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
HUMAN_CHAT_ID      = int(os.environ.get("HUMAN_CHAT_ID", "6224744296"))


def send_message(text: str, chat_id: int = None, reply_markup: dict = None) -> dict:
    """Send a Telegram message. Returns Telegram API response dict."""
    if not TELEGRAM_BOT_TOKEN:
        log.warning("telegram_send_skipped: TELEGRAM_BOT_TOKEN not set")
        return {}

    cid = chat_id or HUMAN_CHAT_ID
    payload: dict = {
        "chat_id": cid,
        "text": text[:4000],
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    data = json.dumps(payload).encode()
    req = _ur.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with _ur.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error("telegram_send_failed error=%s", e)
        return {}


def send_approval_request(task_id: str, agent_type: str, agent_level: int,
                           agent_goal: str, task_title: str, proposed_action: str,
                           revenue_impact: int, urgency: int, confidence: int) -> dict:
    """Send HIGH-risk approval request with inline keyboard."""
    text = (
        f"🚨 *HIGH-RISK TASK — APPROVAL REQUIRED*\n\n"
        f"Agent: `{agent_type}` (Level {agent_level})\n"
        f"Goal: {agent_goal[:100]}\n\n"
        f"*Task:* {task_title}\n"
        f"*Action:* {proposed_action[:300]}\n\n"
        f"Revenue Impact: {revenue_impact}/10 | "
        f"Urgency: {urgency}/10 | "
        f"Confidence: {confidence}/10\n\n"
        f"Task ID: `{task_id}`"
    )
    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ APPROVE", "callback_data": f"approve:{task_id}"},
            {"text": "❌ DENY",    "callback_data": f"deny:{task_id}"},
        ]]
    }
    return send_message(text, reply_markup=reply_markup)

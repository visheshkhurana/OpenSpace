"""
Cleya founder agent — wakes on a schedule, runs one OpenSpace cycle with the
cleya-founder skill, journals to /data/cleya/, decides if a Telegram ping is
warranted.

Env required:
  OPENAI_API_KEY
  TELEGRAM_BOT_TOKEN
  HUMAN_CHAT_ID
  CYCLE_INTERVAL_HOURS  (default 3)
  OPENSPACE_MODEL       (default openai/gpt-4o-mini)
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from openspace import OpenSpace, OpenSpaceConfig

# --- config ---
OPENAI_KEY     = os.environ["OPENAI_API_KEY"]
TG_TOKEN       = os.environ["TELEGRAM_BOT_TOKEN"]
HUMAN_CHAT_ID  = os.environ["HUMAN_CHAT_ID"]
INTERVAL_HOURS = int(os.environ.get("CYCLE_INTERVAL_HOURS", "3"))
MODEL          = os.environ.get("OPENSPACE_MODEL", "openai/gpt-4o-mini")
DATA_ROOT      = Path("/data/cleya")
STATE_FILE     = DATA_ROOT / "state.json"
JOURNAL_DIR    = DATA_ROOT / "journal"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("cleya-founder")


def ensure_state():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps({
            "cycle_number": 0,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_cycle_at_utc": None,
            "target_arpu_inr": 999,
            "target_mrr_usd": 50000,
            "current_mrr_inr": 0,
            "last_telegram_at_utc": None,
            "last_daily_digest_date_ist": None,
        }, indent=2))
        log.info("initialized fresh state at %s", STATE_FILE)


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text())


def save_state(s: dict):
    STATE_FILE.write_text(json.dumps(s, indent=2))


def in_daily_digest_window_ist(now_utc: datetime) -> bool:
    """9am IST = 03:30 UTC. Return True if we're within 30 min of that."""
    ist = now_utc + timedelta(hours=5, minutes=30)
    return ist.hour == 9 and ist.minute < 30


def days_into_program(state: dict) -> int:
    started = datetime.fromisoformat(state["started_at_utc"])
    return (datetime.now(timezone.utc) - started).days + 1


def build_cycle_prompt(state: dict) -> str:
    cycle = state["cycle_number"] + 1
    day = days_into_program(state)
    last_journal = ""
    journals = sorted(JOURNAL_DIR.glob("*.md"))
    if journals:
        last_journal = journals[-1].read_text()[-2000:]

    return f"""You are running cycle #{cycle} of the Cleya founder agent.
Day {day} of the 90-day plan.

CURRENT STATE:
{json.dumps(state, indent=2)}

LAST JOURNAL ENTRY (truncated):
{last_journal or "(none yet — this is the first real cycle)"}

YOUR TASK FOR THIS CYCLE:
Apply the cleya-founder skill. Specifically:

1. Read state, OKRs, last journal entries from /data/cleya/.
2. If files in /data/cleya/ don't exist yet (state.json, okrs.md, product/spec.md, growth/channels.md, research/competitors.md, research/icp.md, research/quotes.md, finance/mrr.md, ops/risks.md, daily/<today>.md), CREATE them with sensible v1 content. This is mandatory on cycle 1.
3. Pick the highest-leverage action using the Leverage Rubric in the skill.
4. Do that action. If it requires web research, use curl. If drafting content, save it to the right /data/cleya/ subfolder marked [DRAFT].
5. Update relevant files.
6. Append a new journal entry to /data/cleya/journal/cycle_{cycle:04d}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md with this format:

   # Cycle {cycle} — Day {day}
   ## What I did
   ## What I learned
   ## What I'm doing next cycle
   ## Files updated
   ## Telegram digest? (yes/no, if yes paste the message)

7. If today is the daily digest window (09:00 IST), draft a digest message to print at the end starting with the marker `<<<TG_DIGEST>>>` on its own line, then the message, then `<<<END_TG_DIGEST>>>` — the runner will send it.
8. If you are blocked needing a credential or human decision, draft a message starting with `<<<TG_BLOCKED>>>` and ending `<<<END_TG_BLOCKED>>>`.
9. If you found something genuinely actionable (high-intent prospect, viral moment, competitor move), draft starting with `<<<TG_DISCOVERY>>>` and ending `<<<END_TG_DISCOVERY>>>`.

End with the marker `<COMPLETE>` when done.
"""


def extract_telegram_message(text: str) -> tuple[str | None, str | None]:
    """Return (kind, message) if any TG marker found, else (None, None)."""
    for kind, start, end in [
        ("DIGEST", "<<<TG_DIGEST>>>", "<<<END_TG_DIGEST>>>"),
        ("BLOCKED", "<<<TG_BLOCKED>>>", "<<<END_TG_BLOCKED>>>"),
        ("DISCOVERY", "<<<TG_DISCOVERY>>>", "<<<END_TG_DISCOVERY>>>"),
    ]:
        if start in text and end in text:
            msg = text.split(start, 1)[1].split(end, 1)[0].strip()
            if msg:
                return kind, msg
    return None, None


def send_telegram(text: str) -> bool:
    import urllib.request
    import urllib.parse
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": int(HUMAN_CHAT_ID),
        "text": text[:4000],
        "parse_mode": "Markdown",
    }).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = json.loads(resp.read()).get("ok", False)
            log.info("telegram send: %s", ok)
            return ok
    except Exception as e:
        log.exception("telegram send failed: %s", e)
        return False


async def run_one_cycle():
    ensure_state()
    state = load_state()
    cycle = state["cycle_number"] + 1
    log.info("=== starting cycle %d (day %d) ===", cycle, days_into_program(state))

    prompt = build_cycle_prompt(state)
    cfg = OpenSpaceConfig(llm_model=MODEL)

    try:
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(prompt)
    except Exception as e:
        log.exception("cycle %d failed: %s", cycle, e)
        return

    response = result.get("response") or result.get("output") or ""
    log.info("cycle %d output (%d chars)", cycle, len(response))

    # extract any Telegram message from output
    now = datetime.now(timezone.utc)
    kind, msg = extract_telegram_message(response)
    if kind == "DIGEST":
        today_ist = (now + timedelta(hours=5, minutes=30)).date().isoformat()
        if state.get("last_daily_digest_date_ist") != today_ist:
            if send_telegram(msg):
                state["last_telegram_at_utc"] = now.isoformat()
                state["last_daily_digest_date_ist"] = today_ist
        else:
            log.info("digest already sent today, skipping")
    elif kind in ("BLOCKED", "DISCOVERY"):
        if send_telegram(f"*[{kind}]*\n\n{msg}"):
            state["last_telegram_at_utc"] = now.isoformat()

    # bump state
    state["cycle_number"] = cycle
    state["last_cycle_at_utc"] = now.isoformat()
    save_state(state)
    log.info("=== cycle %d complete ===", cycle)


async def main():
    log.info(
        "Cleya founder agent starting. interval=%dh model=%s data_root=%s",
        INTERVAL_HOURS, MODEL, DATA_ROOT,
    )
    # Run immediately on boot, then every interval
    while True:
        try:
            await run_one_cycle()
        except Exception:
            log.exception("cycle crashed; will retry next interval")
        sleep_s = INTERVAL_HOURS * 3600
        log.info("sleeping %d seconds until next cycle", sleep_s)
        await asyncio.sleep(sleep_s)


if __name__ == "__main__":
    asyncio.run(main())

"""
OpenSpace Telegram Bot
- Text in/out + voice in (Whisper) + voice out (OpenAI TTS)
- Talks to local OpenSpace via the Python API
- Skill DB is restored from your Supabase bucket on boot, replicated continuously
- Allowlist enforces single-user access
"""
import asyncio
import os
import logging
import tempfile
import io
from pathlib import Path

from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import AsyncOpenAI
from openspace import OpenSpace, OpenSpaceConfig

# ---------- config ----------
BOT_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_IDS   = {int(x) for x in os.environ["TELEGRAM_ALLOWED_IDS"].split(",") if x.strip()}
OPENAI_KEY    = os.environ["OPENAI_API_KEY"]
TTS_VOICE     = os.environ.get("TTS_VOICE", "alloy")           # alloy | echo | fable | onyx | nova | shimmer
# TTS off by default — your OpenAI project must explicitly enable a TTS model.
# Flip on with /tts_on once tts-1 or gpt-4o-mini-tts is enabled in your project.
TTS_ENABLED   = os.environ.get("TTS_ENABLED", "false").lower() == "true"
# Default model: OpenAI via litellm provider prefix (openspace uses litellm under the hood)
MODEL         = os.environ.get("OPENSPACE_MODEL", "openai/gpt-4o-mini")
TTS_MODEL     = os.environ.get("TTS_MODEL", "tts-1")           # tts-1 is in every project; gpt-4o-mini-tts requires opt-in

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("openspace-bot")
openai = AsyncOpenAI(api_key=OPENAI_KEY)

# ---------- guards ----------
def allowed(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    ok = uid in ALLOWED_IDS
    if not ok:
        log.warning("rejected user_id=%s username=%s", uid, update.effective_user.username if update.effective_user else None)
    return ok

# ---------- handlers ----------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text(
        "OpenSpace bot online. Send me text or a voice note.\n"
        "Commands: /skills /tts_on /tts_off /model"
    )

async def cmd_skills(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    import sqlite3
    db = Path(os.environ.get("OPENSPACE_DB_PATH", "/data/openspace/.openspace/openspace.db"))
    if not db.exists():
        await update.message.reply_text("No skill DB yet — run a task first.")
        return
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT name, lineage_origin, datetime(first_seen) "
            "FROM skill_records ORDER BY first_seen DESC LIMIT 20"
        ).fetchall()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"DB read error: {e}")
        return
    if not rows:
        await update.message.reply_text("Skill DB empty.")
        return
    msg = "Latest skills:\n" + "\n".join(f"• {n} ({o}) — {ts}" for n, o, ts in rows)
    await update.message.reply_text(msg[:4000])

async def cmd_tts_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    ctx.bot_data["tts"] = True
    await update.message.reply_text("Voice replies ON")

async def cmd_tts_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    ctx.bot_data["tts"] = False
    await update.message.reply_text("Voice replies OFF")

async def cmd_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    args = ctx.args
    if not args:
        cur = ctx.bot_data.get("model", MODEL)
        await update.message.reply_text(f"Current model: {cur}\nUsage: /model <provider/name>")
        return
    ctx.bot_data["model"] = args[0]
    await update.message.reply_text(f"Model set to {args[0]}")

# ---------- core: run a task through OpenSpace ----------
async def run_openspace(task: str, model: str) -> str:
    log.info("running task: %s", task[:80])
    try:
        cfg = OpenSpaceConfig(llm_model=model)
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(task)
            response = result.get("response") or result.get("output") or "(no response)"
            evolved = result.get("evolved_skills", [])
            if evolved:
                response += f"\n\n[evolved {len(evolved)} skill(s): " + ", ".join(s.get("name", "?") for s in evolved) + "]"
            return response
    except Exception as e:
        log.exception("openspace failed")
        return f"⚠️ OpenSpace error: {e}"

async def synthesize_voice(text: str) -> bytes:
    # Truncate for sane voice notes — long texts get a text reply too
    snippet = text[:1500]
    resp = await openai.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=snippet,
        response_format="opus",
    )
    return resp.content

async def transcribe_voice(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        with open(path, "rb") as fh:
            r = await openai.audio.transcriptions.create(model="whisper-1", file=fh)
        return r.text.strip()
    finally:
        os.unlink(path)

# ---------- text handler ----------
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    task = update.message.text
    await ctx.bot.send_chat_action(update.effective_chat.id, constants.ChatAction.TYPING)
    model = ctx.bot_data.get("model", MODEL)
    reply = await run_openspace(task, model)
    await update.message.reply_text(reply[:4000])
    if ctx.bot_data.get("tts", TTS_ENABLED):
        try:
            audio = await synthesize_voice(reply)
            await update.message.reply_voice(voice=io.BytesIO(audio))
        except Exception as e:
            log.warning("tts failed: %s", e)

# ---------- voice handler ----------
async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, constants.ChatAction.RECORD_VOICE)
    voice = update.message.voice or update.message.audio
    file = await ctx.bot.get_file(voice.file_id)
    buf = bytearray()
    async for chunk in await file.download_as_bytearray_iter() if hasattr(file, "download_as_bytearray_iter") else []:
        buf.extend(chunk)
    if not buf:
        # Fallback for older PTB versions
        b = await file.download_as_bytearray()
        buf = bytearray(b)
    transcript = await transcribe_voice(bytes(buf))
    await update.message.reply_text(f"🎤 \"{transcript}\"")
    await ctx.bot.send_chat_action(update.effective_chat.id, constants.ChatAction.TYPING)
    model = ctx.bot_data.get("model", MODEL)
    reply = await run_openspace(transcript, model)
    await update.message.reply_text(reply[:4000])
    if ctx.bot_data.get("tts", TTS_ENABLED):
        try:
            audio = await synthesize_voice(reply)
            await update.message.reply_voice(voice=io.BytesIO(audio))
        except Exception as e:
            log.warning("tts failed: %s", e)

# ---------- main ----------
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["tts"] = TTS_ENABLED
    app.bot_data["model"] = MODEL
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("tts_on", cmd_tts_on))
    app.add_handler(CommandHandler("tts_off", cmd_tts_off))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app

if __name__ == "__main__":
    app = build_app()
    log.info("Bot starting. Allowed IDs: %s, Model: %s, TTS: %s", ALLOWED_IDS, MODEL, TTS_ENABLED)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

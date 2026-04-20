# OpenSpace Telegram Bot

Run OpenSpace from your phone. Voice in (Whisper), voice out (OpenAI TTS), text both ways. Plugged into the same shared Supabase skill DB as your laptop.

## What you get

- Send a text or voice note from Telegram → it runs through OpenSpace → reply in text + voice
- `/skills` lists your most recently evolved skills
- `/tts_on` `/tts_off` toggles voice replies
- `/model openai/gpt-4o` swaps the backbone LLM at runtime
- Allowlist locks the bot to your Telegram user ID

## Architecture

```
Phone (Telegram)
   │
   ▼
Fly.io container (Mumbai region)
   ├── python-telegram-bot   ← long-polls Telegram
   ├── openspace             ← runs tasks, evolves skills
   └── litestream            ← restores DB on boot, replicates to Supabase
                                  ▲
                                  │
                                  ▼
              Your existing Supabase bucket: openspace-db
                                  ▲
                                  │
                                  ▼
                  Your Mac mini (same shared DB)
```

## Deploy

Prerequisites:
- Telegram bot token (from @BotFather)
- Your Telegram user ID (from @userinfobot)
- Fly.io account + auth token
- The Supabase S3 keys you already have

```bash
cd setup-kit/telegram-bot

flyctl auth token  # paste your token when prompted, or:  export FLY_API_TOKEN=...

flyctl launch --copy-config --no-deploy   # creates the app

flyctl secrets set \
  TELEGRAM_BOT_TOKEN="<from BotFather>" \
  TELEGRAM_ALLOWED_IDS="<your numeric ID>" \
  OPENAI_API_KEY="sk-..." \
  SUPABASE_S3_KEY_ID="eaec422f155925b0ef07b2be658accad" \
  SUPABASE_S3_SECRET="834f94191ba90600f299600059f11cfdb56cc86e38b324080e297d4b1d557265"

flyctl volumes create openspace_data --region bom --size 1
flyctl deploy
flyctl logs   # watch the boot
```

## First-time use

Open Telegram → message your bot:

```
/start
list the 3 most recent OpenAI model releases
```

It thinks for ~10s then replies with text + voice.

Voice test: hold the mic button, say "what's two plus two", release. Bot transcribes and answers.

## Sharing skills with your Mac mini

Both your laptop and the Fly bot write to the same Supabase bucket but under
different `DEVICE_ID` prefixes (`fly-bot` vs your hostname). To pull skills
your laptop evolved into the bot:

```bash
flyctl ssh console
DEVICE_ID=<your-mac-hostname> litestream restore \
  -config /etc/litestream.yml \
  -o /tmp/laptop.db \
  /data/openspace/.openspace/openspace.db
# then merge or swap as needed
```

For most use cases, just pick "the bot is the source of truth" or "the laptop
is the source of truth" and let the other one sync TO it.

## Costs

- **Fly.io:** free tier covers a 512MB always-on VM in one region
- **OpenAI:** Whisper $0.006/min, gpt-4.1 ~$0.003/1k input tokens, TTS $0.015/1k chars
- **Supabase:** already $10/mo (the project you created)

A typical day of bot use (~20 voice messages, ~50 text exchanges) is ~$0.50 in OpenAI costs, dropping over time as skills accumulate.

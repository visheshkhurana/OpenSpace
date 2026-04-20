---
name: notes
description: Save, list, and search personal notes on the bot's persistent disk. Use when the user says "note:", "save note", "remember that", "what notes did I save", "find note", "search notes", or asks to recall something they previously saved.
---

# Notes

Personal note storage on the bot's persistent disk at `/data/notes/`.
Notes survive redeploys and are replicated to Supabase via Litestream
(if you place them inside the `.openspace/` tree — but for these
freeform notes we just keep them on the disk as plain markdown files).

## Storage layout

```
/data/notes/
  2026-04-21.md       # one file per day, append-only
  2026-04-22.md
  ...
```

Each entry inside a daily file:
```
## 14:23 IST
bought groceries at d-mart
```

## Save a note

The user message will look like one of:
- `note: <text>`
- `save note <text>`
- `remember that <text>`
- `note <text>`

Action:
```bash
DATE=$(TZ=Asia/Kolkata date +%Y-%m-%d)
TIME=$(TZ=Asia/Kolkata date +%H:%M)
mkdir -p /data/notes
echo -e "\n## ${TIME} IST\n${TEXT}" >> "/data/notes/${DATE}.md"
```

Reply: `✓ saved (today's note count: N)` where N = grep -c '^## ' that file.

## List notes

User says: `notes today`, `notes yesterday`, `list notes`, `show my notes`.

```bash
# today
cat "/data/notes/$(TZ=Asia/Kolkata date +%Y-%m-%d).md"
# yesterday
cat "/data/notes/$(TZ=Asia/Kolkata date -d 'yesterday' +%Y-%m-%d).md"
# all
ls -la /data/notes/
```

Reply with the actual note content, formatted readably.

## Search notes

User says: `find note <keyword>`, `search notes <keyword>`, `did I note anything about X`.

```bash
grep -rn -i -B 1 "<keyword>" /data/notes/ | head -50
```

Reply with matching lines + which day they were from.

## Tips

- Always TZ as `Asia/Kolkata` (user is in IST).
- If `/data/notes/` doesn't exist, create it.
- Never delete or overwrite a note unless user explicitly says "delete note from <date>".
- If the user just says "what did I do today" — list today's notes.

---
name: url-summary
description: Fetch any URL the user pastes and produce a concise summary. Auto-detects YouTube vs article. Use when the user pastes a link with no other instruction, or says "summarize this", "tldr this link", "what is this article about".
---

# URL Summary

Take a URL and return a tight summary suitable for a Telegram message
(under ~1500 chars).

## Detection

- `youtube.com/watch?v=` or `youtu.be/` → YouTube path
- Anything else → article path

## YouTube path

1. Try transcript via `yt-dlp --skip-download --write-auto-sub --sub-lang en --convert-subs vtt -o '/tmp/yt.%(ext)s' <URL>` (yt-dlp is pre-installed in the container).
2. Strip VTT tags from `/tmp/yt.en.vtt` → plain text.
3. Summarize: title (1 line), 3-5 bullet key points, total length under 1500 chars.

If transcript unavailable, just fetch the page metadata (title + description) and summarize.

## Article path

1. `curl -sL -A 'Mozilla/5.0 (compatible; openspace-bot/1.0)' --max-time 20 <URL> > /tmp/page.html`
2. Extract main text. Quick approach with `python3`:
   ```python
   import re, sys
   html = open('/tmp/page.html').read()
   # strip script/style
   html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S|re.I)
   # strip tags
   text = re.sub(r'<[^>]+>', ' ', html)
   text = re.sub(r'\s+', ' ', text).strip()
   print(text[:8000])
   ```
3. Summarize that text into 5-8 sentences max + the original title if you can extract it from `<title>`.

## Output format

```
📄 <title>
<one-paragraph summary>

Key points:
• point 1
• point 2
• point 3

Source: <URL>
```

## Tips

- Keep replies under ~1500 chars (Telegram readability).
- If the page returns a paywall or login wall, say so explicitly.
- If the URL 404s, say "page not found".
- Never invent content — only summarize what's actually fetched.

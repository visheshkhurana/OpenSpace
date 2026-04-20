---
name: quick-lookups
description: Fast one-shot answers for common lookups — currency conversion, time in any city, weather, whois, DNS records, IP info, hash generation, password generation. Use whenever the user asks any of these.
---

# Quick Lookups

A grab-bag of fast utilities. Pick the right one based on the user's intent.

## Currency conversion

User: `47000 inr to usd`, `100 usd in eur`, `convert 5000 jpy to inr`

```bash
# Free, no key required:
curl -s 'https://open.er-api.com/v6/latest/INR' | python3 -c 'import sys,json;d=json.load(sys.stdin);r=d["rates"]["USD"];print(round(47000*r,2),"USD")'
```

Generic pattern:
```
RATES=$(curl -s "https://open.er-api.com/v6/latest/${FROM}")
RATE=$(echo "$RATES" | python3 -c "import sys,json;print(json.load(sys.stdin)['rates']['${TO}'])")
python3 -c "print(round(${AMOUNT} * ${RATE}, 2))"
```

Reply: `47000 INR ≈ 564.20 USD (rate 1 INR = 0.0120 USD)`

## Time in any city

User: `time in tokyo`, `what time is it in london`

```bash
TZ='Asia/Tokyo' date '+%a %Y-%m-%d %H:%M %Z'
```

Common TZs: `Asia/Tokyo`, `Asia/Kolkata`, `Asia/Singapore`, `America/New_York`,
`America/Los_Angeles`, `Europe/London`, `Europe/Berlin`, `Australia/Sydney`, `UTC`.

## Weather

User: `weather mumbai`, `weather in new york`

```bash
curl -s "https://wttr.in/${CITY}?format=%l:+%C+%t+(feels+%f)+|+humidity+%h+|+wind+%w"
```

Returns one line, perfect for Telegram.

## DNS / IP / whois

```bash
# A records
dig +short example.com A
# MX
dig +short example.com MX
# All (short)
dig +noall +answer example.com ANY
# Whois (concise)
whois example.com 2>/dev/null | grep -iE '^(domain|registrar|creation|expir|name server)' | head -10
# IP geolocation
curl -s "https://ipapi.co/${IP}/json/" | python3 -m json.tool
```

## Hashes & passwords

```bash
# sha256 of a string
echo -n "${TEXT}" | sha256sum | awk '{print $1}'
# md5
echo -n "${TEXT}" | md5sum | awk '{print $1}'
# secure password (24 chars, alnum + symbols)
openssl rand -base64 32 | tr -d '/+=' | head -c 24; echo
# UUID
uuidgen
```

## HTTP status / health check

User: `is openai.com up`, `check status of <URL>`

```bash
curl -s -o /dev/null -w "HTTP %{http_code} — %{time_total}s — %{size_download} bytes\n" --max-time 15 "${URL}"
```

## Tips

- Always echo the answer in a Telegram-friendly one-liner where possible.
- For currency, show the rate so the user can sanity-check.
- For weather, use `wttr.in` — no API key, returns plain text.
- If a tool is missing in the container (e.g. `whois`), fall back to `curl https://rdap.org/domain/<name>`.

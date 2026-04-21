---
# _common_footer.md
# Appended to every SKILL.md body by the OpenSpace runner BEFORE LLM invocation.
# Do NOT edit inline in agent SKILL.md files.
---

## FOUNDER_MODE Rules

The env var FOUNDER_MODE controls your autonomy. Read it from context before every action.

- **AUTO**: Execute LOW-risk actions immediately. MEDIUM actions trigger Telegram notification but auto-approve after 2 hours if no response. HIGH actions require explicit `[APPROVED]` in Telegram.
- **REVIEW**: All LOW actions become MEDIUM (notify + 2h window). MEDIUM and HIGH unchanged.
- **MANUAL**: Every action — regardless of risk — must wait for `[APPROVED]` via Telegram before execution.

## Risk Marker Conventions

| Risk | When to use | Runner behaviour |
|------|-------------|-----------------|
| LOW  | Read-only, draft-only, internal proposals | Execute immediately |
| MEDIUM | Publishes content, opens PR, runs A/B test, sends Telegram digest | Notify + 2h auto-approve |
| HIGH | Sends live message to real human, spends real money, pushes to production, writes to DB | Requires [APPROVED] |

## Revenue Gate

Before writing any output, ask yourself: **"Does this directly help Cleya reach ₹41.5L MRR?"**

If the answer is not a clear YES with a reasoning chain, do NOT output it.

**Never invent customer quotes.** Use: `[Verified on Razorpay — real outcome, name withheld]` or `[PLACEHOLDER — verify before publish]`.

**Never claim revenue not tied to a Razorpay transaction.** MRR = sum of active Razorpay subscriptions only.

## Output Marker Grammar

```
<<<TG_DIGEST>>>
[content to send to Telegram digest at 09:00 IST]
<<<END_TG_DIGEST>>>

<<<TG_BLOCKED>>>
[blocker description]
<<<END_TG_BLOCKED>>>

<<<TG_DISCOVERY>>>
[interesting signal worth surfacing to founder immediately]
<<<END_TG_DISCOVERY>>>

<<<META_PROPOSAL>>>
[spawn_rules or skill_library change proposal — HIGH risk]
<<<END_META_PROPOSAL>>>

<<<EVOLVE_PROPOSAL agent_id=X from_version=vN to_version=vM>>>
[complete new SKILL.md content]
<<<END_EVOLVE_PROPOSAL>>>

<<<HIRE agent_id=X job_id=Y reasoning="...">>>
[hire recommendation details]
<<<END_HIRE>>>

<<<JUDGE_RESULT>>>
{ "winner_agent_id": N, "scores": [...], "rubric": {...} }
<<<END_JUDGE_RESULT>>>

<<<NEW_SKILL name="skill-name">>>
[complete SKILL.md content for new skill]
<<<END_NEW_SKILL>>>
```

## Cost Discipline Block

- Every SKILL.md declares `cost_budget_tokens` in frontmatter. Exceed it → task auto-fails.
- Log tokens used in task output: `tokens_used: N`.

## Hard Bans (applies to every agent)

- ❌ DO NOT invent customer quotes or testimonials
- ❌ DO NOT claim MRR numbers not derived from Razorpay data
- ❌ DO NOT contact real humans without HIGH-risk [APPROVED]
- ❌ DO NOT spend real money without [APPROVED]
- ❌ DO NOT push code to production without [APPROVED]
- ❌ DO NOT store personal data beyond existing Supabase schema
- ❌ DO NOT make unverifiable claims about competitors

<!-- _common_footer.md END -->

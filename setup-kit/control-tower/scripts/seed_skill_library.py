"""
Seed the skill_library table with 24 primitives.
Safe to run multiple times (ON CONFLICT DO NOTHING).
"""
import os
import json
from supabase import create_client

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

SKILLS = [
    {"name": "scraping", "description": "Collect structured data from public web pages", "prompt_fragment": "Extract structured data from the provided URLs. Return JSON array with fields: name, url, role, company, location, contact_hint. Skip duplicates. Flag any page that returns 4xx/5xx.", "tools": ["http_get","html_parser"], "cost_profile": {"avg_tokens_per_task": 800}, "default_risk": "LOW"},
    {"name": "enrichment", "description": "Enrich a lead with company size, funding stage, tech stack", "prompt_fragment": "Given a company name and founder name, enrich with: funding_stage, employee_count, tech_stack_hint, linkedin_url, last_funding_date. Use public signals only.", "tools": ["http_get","supabase_read"], "cost_profile": {"avg_tokens_per_task": 600}, "default_risk": "LOW"},
    {"name": "icp_filtering", "description": "Score a lead against Cleya ICP", "prompt_fragment": "Score this lead 0-10 for ICP fit. ICP: Indian startup founder, pre-Series B, needs warm investor/partner introductions. Return score, top 2 fit reasons, top 1 disqualifier.", "tools": ["supabase_read","llm_score"], "cost_profile": {"avg_tokens_per_task": 400}, "default_risk": "LOW"},
    {"name": "copywriting_in", "description": "Analyse existing copy for clarity, tone, ICP fit, objection gaps", "prompt_fragment": "Analyse the provided copy. Rate: clarity (1-10), ICP alignment (1-10), objection coverage (1-10). List top 3 weaknesses with specific line references. Do not rewrite yet.", "tools": ["llm_analyse"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "copywriting_out", "description": "Generate on-brand copy in India-startup-founder voice", "prompt_fragment": "Write copy that is direct, ambitious, numbers-first. Use INR. Reference Indian startup ecosystem. No corporate jargon. Max 80% of word count target.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 600}, "default_risk": "LOW"},
    {"name": "ab_testing", "description": "Design A/B test with hypothesis, variants, success metric", "prompt_fragment": "Design an A/B test. Output: hypothesis (if-then-because), control description, variant description, primary metric, minimum detectable effect, estimated days to significance.", "tools": ["llm_generate","supabase_read"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "funnel_analytics", "description": "Query funnel metrics; identify biggest drop-off", "prompt_fragment": "Read the metrics table for the last 7 days. Compute: visit_to_signup_rate, signup_to_demo_rate, demo_to_trial_rate, trial_to_paid_rate. Identify the single step with the largest absolute drop.", "tools": ["supabase_read","plausible_api"], "cost_profile": {"avg_tokens_per_task": 400}, "default_risk": "LOW"},
    {"name": "ux_critique", "description": "Audit a screen/flow for friction and drop-off risk", "prompt_fragment": "Review the described UI flow. Identify up to 5 friction points ordered by severity. For each: screen name, issue, user impact, one-line fix recommendation.", "tools": ["llm_analyse"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "objection_handling", "description": "Map sales objections to rebuttals for Indian startup founders", "prompt_fragment": "For each objection listed, write a 2-sentence rebuttal that acknowledges the concern and pivots to Cleya value with a specific number.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 400}, "default_risk": "LOW"},
    {"name": "cold_email", "description": "Draft personalised cold outreach email under 150 words", "prompt_fragment": "Write a cold email: subject line (max 8 words), opener referencing something specific about the recipient, one-line value prop with INR or time saved, single CTA.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "linkedin_dm", "description": "Draft short warm LinkedIn DM referencing mutual context", "prompt_fragment": "Write a LinkedIn DM under 75 words. Open with a genuine observation. State why Cleya is relevant to them right now. End with a low-friction ask.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 400}, "default_risk": "LOW"},
    {"name": "twitter_threading", "description": "Draft 8-12 tweet viral thread for Indian founder/VC audience", "prompt_fragment": "Write a Twitter thread. Tweet 1: bold hook. Tweets 2-10: insight chain, each tweet standalone-readable. Last tweet: CTA + Cleya mention. Each tweet ≤280 chars.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 700}, "default_risk": "LOW"},
    {"name": "razorpay_queries", "description": "Read Razorpay payment data: MRR, plan distribution, failed payments", "prompt_fragment": "Query the razorpay_payments view. Return: mrr_inr, plan_distribution, failed_payment_count_7d, latest_payment_at.", "tools": ["supabase_read"], "cost_profile": {"avg_tokens_per_task": 300}, "default_risk": "LOW"},
    {"name": "plausible_queries", "description": "Fetch Plausible analytics: bounce rate, top pages, traffic sources", "prompt_fragment": "Fetch Plausible data for last 7 days. Return: unique_visitors, bounce_rate, top_5_pages, top_3_sources, goal_completions.", "tools": ["http_get"], "cost_profile": {"avg_tokens_per_task": 300}, "default_risk": "LOW"},
    {"name": "churn_analysis", "description": "Identify churned users, common traits, top-3 churn hypotheses", "prompt_fragment": "From subscriptions table, identify users who cancelled or let trial expire in last 30 days. Return top 3 hypotheses for churn cause with supporting data.", "tools": ["supabase_read","llm_analyse"], "cost_profile": {"avg_tokens_per_task": 600}, "default_risk": "LOW"},
    {"name": "pricing_psychology", "description": "Apply pricing psychology principles to improve pricing page", "prompt_fragment": "Analyse the pricing page against: anchoring, decoy effect, loss aversion, social proof placement. Score each principle 1-5. Suggest top 2 highest-impact changes.", "tools": ["llm_analyse"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "india_gtm", "description": "India-specific GTM tactics: WhatsApp, Telegram, startup communities", "prompt_fragment": "Suggest 5 India-specific distribution tactics for Cleya. For each: effort (1-5), expected leads/week, owner (founder vs agent).", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "vc_warm_intro", "description": "Identify mutual connections for VC/investor warm intro", "prompt_fragment": "Given a target VC and fund, identify 2-3 mutual connection paths. Draft a warm intro request under 100 words. MEDIUM risk — do not send without [APPROVED].", "tools": ["supabase_read","llm_generate"], "cost_profile": {"avg_tokens_per_task": 600}, "default_risk": "MEDIUM"},
    {"name": "deal_room_optimization", "description": "Review Deal Room setup for a match pair; suggest improvements", "prompt_fragment": "Review the Deal Room. Check intro memo completeness, conversation starter quality, suggested documents, expected next step clarity. Output: overall score, top 3 improvements.", "tools": ["llm_analyse"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
    {"name": "indian_founder_voice", "description": "Enforce India-startup-founder tone/style on any text", "prompt_fragment": "Review the text for tone. Flag: corporate jargon, USD amounts (convert to INR), vague claims (replace with specific numbers), passive voice. Return corrected text + change log.", "tools": ["llm_analyse"], "cost_profile": {"avg_tokens_per_task": 300}, "default_risk": "LOW"},
    {"name": "whatsapp_broadcast", "description": "Draft WhatsApp broadcast message: short, actionable, opt-in compliant", "prompt_fragment": "Write a WhatsApp broadcast under 160 chars. Lead with the benefit. Include one link. End with an easy opt-out reminder. Mark MEDIUM risk.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 400}, "default_risk": "MEDIUM"},
    {"name": "landing_page_copy", "description": "Write/rewrite landing page sections for cleya.ai", "prompt_fragment": "Write the requested landing page section. Reference Cleya features: rule + semantic + intent AI matching, warm intros, Deal Room. Include one number in every section. CTA must be action verb + specific benefit.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 700}, "default_risk": "LOW"},
    {"name": "demo_scripting", "description": "Write 10-min product demo script with objection pauses", "prompt_fragment": "Write a demo script for Cleya. Structure: 90s context-setting, 4min core demo, 2min social proof, 2min objection handling, 30s close with Starter INR999/mo CTA. Include PAUSE markers.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 600}, "default_risk": "LOW"},
    {"name": "follow_up_cadences", "description": "Design multi-touch follow-up sequence for trial to paid conversion", "prompt_fragment": "Design a Day 1/3/7/14 follow-up sequence. Each touch: channel (email/WhatsApp/LinkedIn), message angle, CTA, success signal. Day 7 must include pricing objection rebuttal. Day 14 must include urgency element.", "tools": ["llm_generate"], "cost_profile": {"avg_tokens_per_task": 500}, "default_risk": "LOW"},
]

def main():
    inserted = 0
    for skill in SKILLS:
        try:
            db.table("skill_library").insert(skill).execute()
            inserted += 1
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                print(f"  skip (exists): {skill['name']}")
            else:
                print(f"  error {skill['name']}: {e}")
    print(f"Seeded {inserted} skills")

if __name__ == "__main__":
    main()

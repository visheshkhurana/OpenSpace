-- ============================================================
-- CLEYA CONTROL TOWER — MIGRATION 004: SEED DATA
-- ============================================================
BEGIN;

-- ============================================================
-- SEED: skill_library (24 primitives)
-- ============================================================
INSERT INTO skill_library (name, description, prompt_fragment, tools, cost_profile, default_risk)
VALUES
('scraping', 'Collect structured data from public web pages', 'Extract structured data from the provided URLs. Return JSON array with fields: name, url, role, company, location, contact_hint. Skip duplicates. Flag any page that returns 4xx/5xx.', '["http_get","html_parser"]', '{"avg_tokens_per_task":800,"avg_cost_inr":0.07}', 'LOW'),
('enrichment', 'Enrich a lead with company size, funding stage, tech stack, founder LinkedIn URL', 'Given a company name and founder name, enrich with: funding_stage, employee_count, tech_stack_hint, linkedin_url, last_funding_date. Use public signals only. Return null fields if not found.', '["http_get","supabase_read"]', '{"avg_tokens_per_task":600,"avg_cost_inr":0.05}', 'LOW'),
('icp_filtering', 'Score a lead against Cleya ICP', 'Score this lead 0–10 for ICP fit. ICP: Indian startup founder, pre-Series B, needs warm investor/partner introductions, values speed. Return score, top 2 fit reasons, top 1 disqualifier.', '["supabase_read","llm_score"]', '{"avg_tokens_per_task":400,"avg_cost_inr":0.03}', 'LOW'),
('copywriting_in', 'Analyse existing copy for clarity, tone, ICP fit, objection gaps', 'Analyse the provided copy. Rate: clarity (1-10), ICP alignment (1-10), objection coverage (1-10). List top 3 weaknesses with specific line references. Do not rewrite yet.', '["llm_analyse"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('copywriting_out', 'Generate on-brand copy in India-startup-founder voice', 'Write copy that is direct, ambitious, numbers-first. Use INR. Reference Indian startup ecosystem. No corporate jargon. Max 80% of word count target. Always include one concrete number or proof point.', '["llm_generate"]', '{"avg_tokens_per_task":600,"avg_cost_inr":0.05}', 'LOW'),
('ab_testing', 'Design A/B test: hypothesis, variants, success metric, sample size', 'Design an A/B test. Output: hypothesis (if-then-because), control description, variant description, primary metric, minimum detectable effect, estimated days to significance at current traffic.', '["llm_generate","supabase_read"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('funnel_analytics', 'Query funnel metrics; identify biggest drop-off', 'Read the metrics table for the last 7 days. Compute: visit_to_signup_rate, signup_to_demo_rate, demo_to_trial_rate, trial_to_paid_rate. Identify the single step with the largest absolute drop. Return JSON.', '["supabase_read","plausible_api"]', '{"avg_tokens_per_task":400,"avg_cost_inr":0.03}', 'LOW'),
('ux_critique', 'Audit a screen/flow for friction and drop-off risk', 'Review the described UI flow. Identify up to 5 friction points ordered by severity (HIGH/MED/LOW). For each: screen name, issue, user impact, one-line fix recommendation.', '["llm_analyse"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('objection_handling', 'Map sales objections to rebuttals for Indian startup founders', 'For each objection listed, write a 2-sentence rebuttal that: (1) acknowledges the concern, (2) pivots to Cleya value with a specific number. Keep tone peer-to-peer, not salesy.', '["llm_generate"]', '{"avg_tokens_per_task":400,"avg_cost_inr":0.03}', 'LOW'),
('cold_email', 'Draft personalised cold outreach email under 150 words', 'Write a cold email: subject line (max 8 words, no clickbait), opener referencing something specific about the recipient, one-line value prop with ₹ or time saved, single CTA. No attachments mentioned.', '["llm_generate"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('linkedin_dm', 'Draft short warm LinkedIn DM referencing mutual context', 'Write a LinkedIn DM under 75 words. Open with a genuine observation (recent post, shared connection, company milestone). State why Cleya is relevant to them right now. End with a low-friction ask (reply/call/link).', '["llm_generate"]', '{"avg_tokens_per_task":400,"avg_cost_inr":0.03}', 'LOW'),
('twitter_threading', 'Draft 8-12 tweet viral thread for Indian founder/VC audience', 'Write a Twitter thread. Tweet 1: bold hook with a surprising number or contrarian take. Tweets 2-10: insight chain, each tweet standalone-readable. Last tweet: CTA + Cleya mention. Each tweet ≤280 chars.', '["llm_generate"]', '{"avg_tokens_per_task":700,"avg_cost_inr":0.06}', 'LOW'),
('razorpay_queries', 'Read Razorpay payment data: MRR, plan distribution, failed payments', 'Query the razorpay_payments view. Return: mrr_inr (sum of recurring payments last 30d), plan_distribution (count per plan), failed_payment_count_7d, latest_payment_at. All amounts in ₹.', '["supabase_read"]', '{"avg_tokens_per_task":300,"avg_cost_inr":0.02}', 'LOW'),
('plausible_queries', 'Fetch Plausible analytics: bounce rate, top pages, traffic sources', 'Call the Plausible API for the last 7 days. Return: unique_visitors, bounce_rate, top_5_pages (path + visitors), top_3_sources (referrer + visitors), goal_completions (demo_booked, trial_started).', '["http_get"]', '{"avg_tokens_per_task":300,"avg_cost_inr":0.02}', 'LOW'),
('churn_analysis', 'Identify churned users, common traits, top-3 churn hypotheses', 'From subscriptions table, identify users who cancelled or let trial expire in last 30 days. Group by: plan, onboarding_completed (bool), days_active_before_churn, last_feature_used. Return top 3 hypotheses for churn cause, each with supporting data.', '["supabase_read","llm_analyse"]', '{"avg_tokens_per_task":600,"avg_cost_inr":0.05}', 'LOW'),
('pricing_psychology', 'Apply pricing psychology principles to evaluate/improve pricing page', 'Analyse the pricing page against: anchoring (is Pro anchored against Enterprise?), decoy effect (is Starter the decoy?), loss aversion (are trial benefits framed as losses on downgrade?), social proof placement. Score each principle 1-5. Suggest top 2 highest-impact changes.', '["llm_analyse"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('india_gtm', 'India-specific GTM tactics: WhatsApp, Telegram, startup communities', 'Suggest 5 India-specific distribution tactics for Cleya right now. Consider: WhatsApp founder groups, iSPIRT/Headstart communities, YC India alumni, Tier-2 city startup events, vernacular content. For each: effort (1-5), expected leads/week, owner (founder vs agent).', '["llm_generate"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('vc_warm_intro', 'Identify mutual connections for VC/investor warm intro; draft intro request', 'Given a target VC name and fund, identify 2-3 mutual connection paths using known Cleya network. Draft a warm intro request message under 100 words. Mark as MEDIUM risk — do not send without [APPROVED].', '["supabase_read","llm_generate"]', '{"avg_tokens_per_task":600,"avg_cost_inr":0.05}', 'MEDIUM'),
('deal_room_optimization', 'Review Deal Room setup for a match pair; suggest improvements', 'Review the Deal Room between two parties. Check: intro memo completeness (7/10+), conversation starter quality, suggested documents, expected next step clarity. Output: overall score, top 3 improvement suggestions.', '["llm_analyse"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW'),
('indian_founder_voice', 'Enforce India-startup-founder tone/style on any text', 'Review the text for tone. Flag: corporate jargon (replace with direct language), USD amounts (convert to ₹), vague claims (replace with specific numbers), passive voice (rewrite active). Return corrected text + change log.', '["llm_analyse"]', '{"avg_tokens_per_task":300,"avg_cost_inr":0.02}', 'LOW'),
('whatsapp_broadcast', 'Draft WhatsApp broadcast message: short, actionable, opt-in compliant', 'Write a WhatsApp broadcast under 160 chars. Lead with the benefit. Include one link. End with an easy opt-out reminder. Do not use words that trigger spam filters. Mark MEDIUM risk — requires approval before sending.', '["llm_generate"]', '{"avg_tokens_per_task":400,"avg_cost_inr":0.03}', 'MEDIUM'),
('landing_page_copy', 'Write/rewrite landing page sections for cleya.ai', 'Write the requested landing page section. Reference Cleya features: rule + semantic + intent AI matching, warm intros, Deal Room. Use social proof format: "[X founders] got [Y outcome] in [Z days]". Include one number in every section. CTA must be action verb + specific benefit.', '["llm_generate"]', '{"avg_tokens_per_task":700,"avg_cost_inr":0.06}', 'LOW'),
('demo_scripting', 'Write 10-min product demo script with objection pauses and close CTA', 'Write a demo script for Cleya. Structure: 90s context-setting, 4min core demo (3 key features), 2min social proof, 2min objection handling, 30s close with Starter ₹999/mo CTA. Include "[PAUSE — ask question]" markers.', '["llm_generate"]', '{"avg_tokens_per_task":600,"avg_cost_inr":0.05}', 'LOW'),
('follow_up_cadences', 'Design multi-touch follow-up sequence for trial to paid conversion', 'Design a Day 1/3/7/14 follow-up sequence for [segment]. Each touch: channel (email/WhatsApp/LinkedIn), message angle, CTA, success signal. Day 7 must include pricing objection rebuttal. Day 14 must include urgency/scarcity element. All messages under 100 words.', '["llm_generate"]', '{"avg_tokens_per_task":500,"avg_cost_inr":0.04}', 'LOW')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED: spawn_rules (from spec §4 + §3.3)
-- ============================================================
INSERT INTO spawn_rules (name, trigger_metric, operator, threshold, agent_type_to_spawn, goal_template, cooldown_hours, enabled, metadata)
VALUES
('Low leads alert', 'leads_per_day', '<', 5, 'growth-micro', 'Generate {{.value}} additional warm leads today through outreach or content', 4, true, '{"rule_id": "SR-001"}'),
('Low conversion rate', 'conv_rate_pct', '<', 2.0, 'sales-micro', 'Diagnose and fix conversion drop: current rate {{.value}}%', 6, true, '{"rule_id": "SR-002"}'),
('MRR below milestone', 'mrr_inr', '<', 100000, 'growth', 'MRR is ₹{{.value}}. Design and execute plan to reach ₹1,00,000 MRR', 24, true, '{"rule_id": "SR-003"}'),
('High churn signal', 'churn_count', '>', 2, 'product-micro', 'Churn count {{.value}} this week. Interview churned users and propose retention fixes', 12, true, '{"rule_id": "SR-004"}'),
('CAC too high', 'cac_inr', '>', 5000, 'sales-micro', 'CAC ₹{{.value}} exceeds target ₹5000. Audit and optimise acquisition channels', 8, true, '{"rule_id": "SR-005"}'),
('Lead pipeline thin', 'leads_per_day', '<', 15, 'lead-gen', 'Generate minimum 20 qualified leads today from Indian startup ecosystem', 4, true, '{"rule_id": "SR-006"}'),
('Demo conversion low', 'demo_conv_rate', '<', 0.15, 'conversion-optimizer', 'Improve demo-to-trial conversion rate from current value to 0.20+', 6, true, '{"rule_id": "SR-007"}'),
('Low signup-to-demo rate', 'signup_to_demo_rate', '<', 0.30, 'ux', 'Identify and fix the single biggest friction point in signup-to-demo funnel', 6, true, '{"rule_id": "SR-008"}'),
('Trial-to-paid poor', 'trial_to_paid_rate', '<', 0.10, 'retention', 'Improve trial-to-paid conversion to 15%+ within 30 days', 12, true, '{"rule_id": "SR-009"}'),
('MRR declining', 'mrr_weekly_delta_inr', '<', 0, 'content', 'Create 3 viral content pieces this week to drive top-of-funnel signups', 12, true, '{"rule_id": "SR-010"}'),
('High churn rate', 'churn_rate_30d', '>', 0.07, 'retention', 'Reduce 30-day churn rate from current value to below 5%', 24, true, '{"rule_id": "SR-011"}'),
('Landing bounce high', 'landing_bounce_rate', '>', 0.65, 'landing-headline-rewriter', 'Rewrite hero headline and sub-headline to reduce bounce rate below 55%', 48, true, '{"rule_id": "SR-012"}'),
('Pricing page CTR low', 'pricing_page_ctr', '<', 0.08, 'pricing-copy-improver', 'Rewrite pricing page copy to improve CTA click rate above 10%', 48, true, '{"rule_id": "SR-013"}'),
('Low demo bookings', 'demos_booked_today', '<', 5, 'demo', 'Prepare 5 demo scripts and track outcomes to improve demo-to-trial rate', 12, true, '{"rule_id": "SR-014"}'),
('Outreach needed', 'demo_conv_rate', '<', 0.15, 'outreach', 'Draft and queue 50 personalized DM outreach messages to warm leads', 8, true, '{"rule_id": "SR-015"}'),
('Analytics gap', 'tasks_completed_today', '<', 1, 'analytics', 'Compute full funnel metrics and identify single biggest revenue bottleneck', 4, true, '{"rule_id": "SR-016"}'),
('Follow-up needed', 'signup_to_demo_rate', '<', 0.30, 'follow-up', 'Create follow-up cadence for users who signed up but never booked demo', 8, true, '{"rule_id": "SR-017"}'),
('Feature gap discovered', 'feature_requests_pending', '>', 3, 'feature-builder', 'Spec and prioritize top 3 most-requested features with revenue impact analysis', 24, true, '{"rule_id": "SR-018"}')
ON CONFLICT DO NOTHING;

-- ============================================================
-- SEED: Bootstrap agents (Meta always-on)
-- ============================================================
INSERT INTO agents (id, level, type, status, skill_ref, goal, created_by, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    1,
    'meta',
    'active',
    'meta-agent',
    'Orchestrate all Cleya agents to reach ₹41.5L MRR. Read metrics, evaluate spawn rules, enforce caps, emit daily digest.',
    'system',
    '{"bootstrap": true, "always_on": true}'
)
ON CONFLICT (id) DO NOTHING;

COMMIT;

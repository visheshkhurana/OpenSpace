-- ============================================================
-- CLEYA CONTROL TOWER — MIGRATION 003: VIEWS
-- ============================================================
BEGIN;

-- Priority queue view
CREATE OR REPLACE VIEW v_task_priority AS
SELECT
    t.id,
    t.title,
    t.status,
    t.risk_level,
    t.revenue_impact_score,
    t.urgency,
    t.confidence,
    t.priority,
    t.queued_at,
    a.type AS agent_type,
    a.level AS agent_level,
    a.goal AS agent_goal
FROM tasks t
JOIN agents a ON a.id = t.agent_id
WHERE t.status IN ('queued', 'approved')
ORDER BY t.priority DESC, t.queued_at ASC;

-- Agent cost health view
CREATE OR REPLACE VIEW v_agent_cost_health AS
SELECT
    a.id,
    a.type,
    a.level,
    a.status,
    a.tasks_done,
    a.success_rate,
    a.revenue_contrib_inr,
    a.cost_to_date_inr,
    a.token_budget_weekly_inr,
    CASE
        WHEN a.token_budget_weekly_inr > 0
        THEN ROUND(a.cost_to_date_inr / a.token_budget_weekly_inr * 100, 1)
        ELSE 0
    END AS budget_used_pct,
    CASE
        WHEN a.revenue_contrib_inr > 0
        THEN ROUND(a.cost_to_date_inr::NUMERIC / a.revenue_contrib_inr, 4)
        ELSE NULL
    END AS cost_per_revenue_ratio,
    a.tournament_wins,
    a.tournament_losses,
    a.consecutive_kpi_weeks
FROM agents a
WHERE a.status IN ('active', 'pending')
ORDER BY a.level, a.type;

-- Revenue attribution view
CREATE OR REPLACE VIEW v_revenue_attribution AS
SELECT
    a.type AS agent_type,
    a.level,
    COUNT(t.id) AS tasks_completed,
    SUM(CASE WHEN t.outputs->>'revenue_contribution_inr' IS NOT NULL
        THEN (t.outputs->>'revenue_contribution_inr')::NUMERIC
        ELSE 0 END) AS attributed_revenue_inr,
    AVG(t.revenue_impact_score) AS avg_impact_score,
    a.revenue_contrib_inr AS agent_declared_contrib_inr
FROM agents a
LEFT JOIN tasks t ON t.agent_id = a.id AND t.status = 'completed'
GROUP BY a.id, a.type, a.level, a.revenue_contrib_inr
ORDER BY attributed_revenue_inr DESC;

-- Daily digest metrics view
CREATE OR REPLACE VIEW v_digest_metrics AS
SELECT
    (SELECT value FROM metrics WHERE key = 'leads_per_day' ORDER BY ts DESC LIMIT 1) AS leads_per_day,
    (SELECT value FROM metrics WHERE key = 'demos_booked_today' ORDER BY ts DESC LIMIT 1) AS demos_booked_today,
    (SELECT value FROM metrics WHERE key = 'demo_conv_rate' ORDER BY ts DESC LIMIT 1) AS demo_conv_rate,
    (SELECT value FROM metrics WHERE key = 'signup_to_demo_rate' ORDER BY ts DESC LIMIT 1) AS signup_to_demo_rate,
    (SELECT value FROM metrics WHERE key = 'trial_to_paid_rate' ORDER BY ts DESC LIMIT 1) AS trial_to_paid_rate,
    (SELECT value FROM metrics WHERE key = 'mrr_inr' ORDER BY ts DESC LIMIT 1) AS mrr_inr,
    (SELECT value FROM metrics WHERE key = 'mrr_weekly_delta_inr' ORDER BY ts DESC LIMIT 1) AS mrr_weekly_delta_inr,
    (SELECT value FROM metrics WHERE key = 'churn_rate_30d' ORDER BY ts DESC LIMIT 1) AS churn_rate_30d,
    (SELECT value FROM metrics WHERE key = 'landing_bounce_rate' ORDER BY ts DESC LIMIT 1) AS landing_bounce_rate,
    (SELECT COUNT(*) FROM agents WHERE status = 'active' AND level = 2) AS active_l2_agents,
    (SELECT COUNT(*) FROM agents WHERE status = 'active' AND level = 3) AS active_l3_agents,
    (SELECT COUNT(*) FROM tasks WHERE status IN ('queued','approved','executing') AND queued_at > NOW() - INTERVAL '24h') AS tasks_in_flight;

COMMIT;

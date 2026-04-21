-- ============================================================
-- CLEYA CONTROL TOWER — MIGRATION 001: V1 TABLES
-- Project: fhrynagbidbznfvuoxcn (Supabase, ap-south-1)
-- ============================================================
BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================================
-- TABLE: agents
-- ============================================================
CREATE TABLE IF NOT EXISTS agents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level               SMALLINT NOT NULL CHECK (level IN (1, 2, 3)),
    parent_id           UUID REFERENCES agents(id) ON DELETE SET NULL,
    type                TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'active', 'paused', 'killed', 'archived')),
    skill_ref           TEXT NOT NULL,
    goal                TEXT NOT NULL,
    spawned_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    killed_at           TIMESTAMPTZ,
    kill_reason         TEXT,
    revenue_contrib_inr BIGINT NOT NULL DEFAULT 0,
    tasks_done          INTEGER NOT NULL DEFAULT 0,
    success_rate        NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    created_by          TEXT NOT NULL DEFAULT 'meta',
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_agents_level_status ON agents(level, status);
CREATE INDEX IF NOT EXISTS idx_agents_parent_id ON agents(parent_id);
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
CREATE INDEX IF NOT EXISTS idx_agents_spawned_at ON agents(spawned_at DESC);

-- ============================================================
-- TABLE: tasks
-- ============================================================
CREATE TABLE IF NOT EXISTS tasks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id            UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    inputs              JSONB NOT NULL DEFAULT '{}',
    proposed_action     TEXT NOT NULL,
    risk_level          TEXT NOT NULL DEFAULT 'LOW'
                            CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    status              TEXT NOT NULL DEFAULT 'queued'
                            CHECK (status IN (
                                'queued',
                                'claimed',
                                'awaiting_approval',
                                'approved',
                                'denied',
                                'executing',
                                'completed',
                                'failed',
                                'rejected'
                            )),
    outputs             JSONB,
    revenue_impact_score SMALLINT NOT NULL DEFAULT 3
                            CHECK (revenue_impact_score BETWEEN 3 AND 10),
    urgency             SMALLINT NOT NULL DEFAULT 5
                            CHECK (urgency BETWEEN 1 AND 10),
    confidence          SMALLINT NOT NULL DEFAULT 5
                            CHECK (confidence BETWEEN 1 AND 10),
    priority            NUMERIC(10,4) GENERATED ALWAYS AS
                            (revenue_impact_score::NUMERIC * confidence::NUMERIC
                             / GREATEST(urgency::NUMERIC, 1))
                            STORED,
    approval_state      TEXT CHECK (approval_state IN ('pending', 'approved', 'denied')),
    approved_by         TEXT,
    queued_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_at          TIMESTAMPTZ,
    executed_at         TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    worker_id           TEXT,
    error_message       TEXT,
    retry_count         SMALLINT NOT NULL DEFAULT 0,
    max_retries         SMALLINT NOT NULL DEFAULT 2
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_queued ON tasks(status, queued_at)
    WHERE status IN ('queued', 'approved');
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_risk_level ON tasks(risk_level);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_queued_at ON tasks(queued_at DESC);

-- ============================================================
-- TABLE: metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS metrics (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    key         TEXT NOT NULL,
    value       NUMERIC NOT NULL,
    source      TEXT NOT NULL DEFAULT 'cron',
    metadata    JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_metrics_key_ts ON metrics(key, ts DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts DESC);

-- ============================================================
-- TABLE: spawn_rules
-- ============================================================
CREATE TABLE IF NOT EXISTS spawn_rules (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                TEXT NOT NULL,
    trigger_metric      TEXT NOT NULL,
    operator            TEXT NOT NULL CHECK (operator IN ('<', '<=', '>', '>=', '=')),
    threshold           NUMERIC NOT NULL,
    agent_type_to_spawn TEXT NOT NULL,
    goal_template       TEXT NOT NULL,
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    cooldown_hours      INTEGER NOT NULL DEFAULT 4,
    last_fired_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_spawn_rules_enabled ON spawn_rules(enabled);

-- ============================================================
-- TABLE: decisions
-- ============================================================
CREATE TABLE IF NOT EXISTS decisions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    task_id     UUID REFERENCES tasks(id) ON DELETE SET NULL,
    decision    TEXT NOT NULL,
    reasoning   TEXT NOT NULL,
    outcome     TEXT,
    revenue_impact_actual_inr BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_agent_id ON decisions(agent_id);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at DESC);

-- ============================================================
-- TABLE: approvals_inbox
-- ============================================================
CREATE TABLE IF NOT EXISTS approvals_inbox (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         UUID NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
    risk            TEXT NOT NULL DEFAULT 'HIGH',
    telegram_msg_id INTEGER,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded_at    TIMESTAMPTZ,
    decision        TEXT CHECK (decision IN ('approved', 'denied')),
    decided_by      TEXT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_approvals_task_id ON approvals_inbox(task_id);
CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals_inbox(sent_at)
    WHERE decision IS NULL;

-- ============================================================
-- TABLE: agent_audit_log
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_audit_log (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    event       TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}',
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    worker_id   TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_agent_id ON agent_audit_log(agent_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event ON agent_audit_log(event, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON agent_audit_log(ts DESC);

-- ============================================================
-- VIEWS
-- ============================================================
CREATE OR REPLACE VIEW v_active_agents AS
SELECT
    a.id, a.level, a.type, a.status, a.skill_ref, a.goal, a.spawned_at,
    a.tasks_done, a.success_rate, a.revenue_contrib_inr,
    p.type AS parent_type
FROM agents a
LEFT JOIN agents p ON p.id = a.parent_id
WHERE a.status = 'active'
ORDER BY a.level, a.spawned_at;

CREATE OR REPLACE VIEW v_pending_approvals AS
SELECT
    ai.id AS inbox_id, ai.task_id, t.title, t.proposed_action, t.risk_level,
    t.revenue_impact_score, ag.type AS agent_type, ag.level AS agent_level,
    ai.sent_at, EXTRACT(EPOCH FROM (NOW() - ai.sent_at)) / 3600 AS hours_waiting
FROM approvals_inbox ai
JOIN tasks t ON t.id = ai.task_id
JOIN agents ag ON ag.id = t.agent_id
WHERE ai.decision IS NULL
ORDER BY ai.sent_at;

CREATE OR REPLACE VIEW v_latest_metrics AS
SELECT DISTINCT ON (key) key, value, ts, source
FROM metrics
ORDER BY key, ts DESC;

-- ============================================================
-- RPC FUNCTIONS
-- ============================================================
CREATE OR REPLACE FUNCTION claim_next_task(p_worker_id TEXT)
RETURNS SETOF tasks
LANGUAGE plpgsql
AS $$
DECLARE
    claimed_task tasks;
BEGIN
    SELECT * INTO claimed_task
    FROM tasks
    WHERE status IN ('queued', 'approved')
      AND retry_count < max_retries
    ORDER BY priority DESC, queued_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;

    IF claimed_task.id IS NULL THEN
        RETURN;
    END IF;

    UPDATE tasks
    SET status = 'claimed',
        claimed_at = NOW(),
        worker_id = p_worker_id
    WHERE id = claimed_task.id;

    claimed_task.status := 'claimed';
    claimed_task.worker_id := p_worker_id;
    RETURN NEXT claimed_task;
END;
$$;

CREATE OR REPLACE FUNCTION increment_agent_stats(
    p_agent_id UUID,
    p_revenue_inr BIGINT DEFAULT 0
)
RETURNS VOID
LANGUAGE sql
AS $$
    UPDATE agents
    SET tasks_done = tasks_done + 1,
        revenue_contrib_inr = revenue_contrib_inr + p_revenue_inr,
        success_rate = (
            SELECT ROUND(
                (COUNT(*) FILTER (WHERE status = 'completed'))::NUMERIC
                / GREATEST(COUNT(*), 1) * 100,
            2)
            FROM tasks WHERE agent_id = p_agent_id
        )
    WHERE id = p_agent_id;
$$;

CREATE OR REPLACE FUNCTION increment_task_retry(p_task_id UUID)
RETURNS VOID
LANGUAGE sql
AS $$
    UPDATE tasks
    SET retry_count = retry_count + 1
    WHERE id = p_task_id;
$$;

COMMIT;

-- ============================================================
-- CLEYA CONTROL TOWER — MIGRATION 002: V2 WORKFORCE EVOLUTION
-- Run AFTER 001_init.sql
-- ============================================================
BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- pgvector for memory embeddings (install separately if not available)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE: skill_library
-- ============================================================
CREATE TABLE IF NOT EXISTS skill_library (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                TEXT NOT NULL UNIQUE,
    description         TEXT NOT NULL,
    prompt_fragment     TEXT NOT NULL,
    tools               JSONB NOT NULL DEFAULT '[]',
    cost_profile        JSONB NOT NULL DEFAULT '{}',
    default_risk        TEXT NOT NULL DEFAULT 'LOW'
                            CHECK (default_risk IN ('LOW', 'MEDIUM', 'HIGH')),
    avg_quality_score   NUMERIC(4,2) NOT NULL DEFAULT 0.0,
    times_used          INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_library_name    ON skill_library(name);
CREATE INDEX IF NOT EXISTS idx_skill_library_risk    ON skill_library(default_risk);
CREATE INDEX IF NOT EXISTS idx_skill_library_quality ON skill_library(avg_quality_score DESC);

-- ============================================================
-- TABLE: agent_skills  (many-to-many)
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_skills (
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id    UUID NOT NULL REFERENCES skill_library(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_skills_skill_id ON agent_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_agent_skills_agent_id ON agent_skills(agent_id);

-- ============================================================
-- TABLE: agent_evolutions
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_evolutions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    from_version    INTEGER NOT NULL,
    to_version      INTEGER NOT NULL,
    change_summary  TEXT NOT NULL,
    reason          TEXT NOT NULL DEFAULT '',
    perf_delta      JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected', 'applied')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_by     TEXT,
    applied_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_evolutions_agent_id   ON agent_evolutions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_evolutions_status     ON agent_evolutions(status);
CREATE INDEX IF NOT EXISTS idx_agent_evolutions_created_at ON agent_evolutions(created_at DESC);

-- ============================================================
-- TABLE: tournaments
-- ============================================================
CREATE TABLE IF NOT EXISTS tournaments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         UUID REFERENCES tasks(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'running', 'judging', 'resolved', 'expired')),
    judge_criteria  JSONB NOT NULL DEFAULT '{"quality": 0.5, "cost": 0.3, "speed": 0.2}',
    winner_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    time_box_hours  INTEGER NOT NULL DEFAULT 48
);

CREATE INDEX IF NOT EXISTS idx_tournaments_status     ON tournaments(status);
CREATE INDEX IF NOT EXISTS idx_tournaments_created_at ON tournaments(created_at DESC);

-- ============================================================
-- TABLE: tournament_entries
-- ============================================================
CREATE TABLE IF NOT EXISTS tournament_entries (
    tournament_id   UUID NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    output_id       UUID REFERENCES tasks(id) ON DELETE SET NULL,
    score           NUMERIC(5,2),
    rubric          JSONB NOT NULL DEFAULT '{}',
    completed_at    TIMESTAMPTZ,
    PRIMARY KEY (tournament_id, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_tournament_entries_agent_id      ON tournament_entries(agent_id);
CREATE INDEX IF NOT EXISTS idx_tournament_entries_tournament_id ON tournament_entries(tournament_id);

-- ============================================================
-- TABLE: job_posts
-- ============================================================
CREATE TABLE IF NOT EXISTS job_posts (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id          UUID REFERENCES tasks(id) ON DELETE SET NULL,
    requirements     JSONB NOT NULL DEFAULT '{}',
    status           TEXT NOT NULL DEFAULT 'open'
                         CHECK (status IN ('open', 'selecting', 'filled', 'closed', 'expired')),
    posted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closes_at        TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 minutes',
    selected_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_job_posts_status    ON job_posts(status);
CREATE INDEX IF NOT EXISTS idx_job_posts_posted_at ON job_posts(posted_at DESC);

-- ============================================================
-- TABLE: applications
-- ============================================================
CREATE TABLE IF NOT EXISTS applications (
    job_post_id           UUID NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,
    agent_id              UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    pitch                 TEXT NOT NULL,
    estimated_cost_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_quality     NUMERIC(4,2) NOT NULL DEFAULT 0.0,
    applied_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (job_post_id, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_job_post_id ON applications(job_post_id);
CREATE INDEX IF NOT EXISTS idx_applications_agent_id   ON applications(agent_id);

-- ============================================================
-- TABLE: teams
-- ============================================================
CREATE TABLE IF NOT EXISTS teams (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          TEXT NOT NULL,
    purpose       TEXT NOT NULL,
    lead_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disbanded_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_teams_lead_agent_id ON teams(lead_agent_id);

-- ============================================================
-- TABLE: memories
-- ============================================================
CREATE TABLE IF NOT EXISTS memories (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id             UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    key                  TEXT NOT NULL,
    value                JSONB NOT NULL,
    -- embedding         vector(1536),  -- uncomment when pgvector is available
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    relevance_decay_days INTEGER NOT NULL DEFAULT 30,
    pinned               BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_memories_agent_id  ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_key       ON memories(key);
CREATE INDEX IF NOT EXISTS idx_memories_last_used ON memories(last_used_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_pinned    ON memories(pinned) WHERE pinned = TRUE;

-- ============================================================
-- ALTER TABLE agents — v2 columns
-- ============================================================
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS version                  INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS parent_version_id        UUID    REFERENCES agents(id),
    ADD COLUMN IF NOT EXISTS team_id                  UUID    REFERENCES teams(id),
    ADD COLUMN IF NOT EXISTS cost_to_date_inr         NUMERIC NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS token_budget_weekly_inr  NUMERIC NOT NULL DEFAULT 500,
    ADD COLUMN IF NOT EXISTS tournament_wins          INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tournament_losses        INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS consecutive_kpi_weeks    INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS founder_mode             TEXT NOT NULL DEFAULT 'AUTO'
                                 CHECK (founder_mode IN ('AUTO', 'REVIEW', 'MANUAL')),
    ADD COLUMN IF NOT EXISTS last_active_at           TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_agents_version       ON agents(version);
CREATE INDEX IF NOT EXISTS idx_agents_team_id       ON agents(team_id);
CREATE INDEX IF NOT EXISTS idx_agents_cost          ON agents(cost_to_date_inr DESC);
CREATE INDEX IF NOT EXISTS idx_agents_tournament    ON agents(tournament_wins DESC, tournament_losses DESC);

-- ============================================================
-- ALTER TABLE spawn_rules — v2 backward-compatible additions
-- ============================================================
ALTER TABLE spawn_rules
    ADD COLUMN IF NOT EXISTS action                TEXT NOT NULL DEFAULT 'spawn'
                                 CHECK (action IN ('spawn', 'route', 'compose', 'recruit', 'kill', 'evolve', 'clone')),
    ADD COLUMN IF NOT EXISTS problem_description   TEXT,
    ADD COLUMN IF NOT EXISTS inherit_from          JSONB DEFAULT '[]';

-- ============================================================
-- FUNCTION: agents_covering_skills
-- ============================================================
CREATE OR REPLACE FUNCTION agents_covering_skills(required_skills TEXT[])
RETURNS TABLE (id UUID, type TEXT, cost_ratio NUMERIC)
LANGUAGE sql STABLE
AS $$
    SELECT
        a.id,
        a.type,
        CASE
            WHEN a.token_budget_weekly_inr = 0 THEN 999
            ELSE a.cost_to_date_inr / a.token_budget_weekly_inr
        END AS cost_ratio
    FROM agents a
    WHERE a.status = 'active'
      AND NOT EXISTS (
          SELECT 1
          FROM unnest(required_skills) rs(name)
          WHERE NOT EXISTS (
              SELECT 1
              FROM agent_skills ags
              JOIN skill_library sl ON sl.id = ags.skill_id
              WHERE ags.agent_id = a.id AND sl.name = rs.name
          )
      )
    ORDER BY cost_ratio ASC;
$$;

-- ============================================================
-- TABLE: founder_mode_config (DB-backed FOUNDER_MODE)
-- ============================================================
CREATE TABLE IF NOT EXISTS founder_mode_config (
    id          BIGSERIAL PRIMARY KEY,
    mode        TEXT NOT NULL DEFAULT 'AUTO'
                    CHECK (mode IN ('AUTO', 'REVIEW', 'MANUAL')),
    set_by      TEXT NOT NULL DEFAULT 'system',
    set_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default
INSERT INTO founder_mode_config (mode, set_by)
VALUES ('AUTO', 'bootstrap')
ON CONFLICT DO NOTHING;

COMMIT;

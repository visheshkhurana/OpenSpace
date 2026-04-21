// ─── Agent / Task core (v1) ──────────────────────────────────────────────────
export type AgentStatus = 'active' | 'idle' | 'failed' | 'killed';
export type AgentLevel = 0 | 1 | 2 | 3;

export interface Agent {
  id: string;
  name: string;
  level: AgentLevel;
  status: AgentStatus;
  parent_id: string | null;
  current_task_id: string | null;
  current_task_summary: string | null;
  revenue_attributed_inr: number;
  success_rate_pct: number;
  task_count_total: number;
  task_count_success: number;
  spawned_at: string;
  killed_at: string | null;
  skill_id: string;
  metadata: Record<string, unknown>;
  children?: string[];

  // v2 additions
  version: number;
  parent_version_id: string | null;
  skills: string[];
  team_id: string | null;
  cost_to_date_inr: number;
  token_budget_weekly: number;
  tokens_used_this_week: number;
  is_clone: boolean;
  tournament_id: string | null;
  crown: boolean;
  avg_tokens_per_task?: number;
}

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'approval_required'
  | 'denied';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface AgentTask {
  id: string;
  agent_id: string;
  agent_name?: string;
  summary: string;
  status: TaskStatus;
  risk: RiskLevel;
  revenue_impact_inr: number;
  urgency: 1 | 2 | 3 | 4 | 5;
  created_at: string;
  completed_at: string | null;
  input_payload: Record<string, unknown>;
  proposed_action: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
}

export interface TaskFilters {
  agent_ids?: string[];
  risk?: RiskLevel[];
  status?: TaskStatus[];
  urgency_min?: number;
  urgency_max?: number;
  revenue_min_inr?: number;
  created_after?: string;
  search?: string;
}

export interface AuditLogLine {
  ts: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  agent_id: string;
}

// ─── Activity feed ───────────────────────────────────────────────────────────
export type ActivityEventType =
  | 'action'
  | 'success'
  | 'failure'
  | 'spawn'
  | 'kill'
  | 'approval_required'
  | 'tournament_started'
  | 'tournament_won'
  | 'agent_evolved'
  | 'skill_composed'
  | 'job_posted'
  | 'applied'
  | 'hired'
  | 'cloned'
  | 'team_formed'
  | 'team_disbanded'
  | 'memory_pinned'
  | 'mode_changed'
  | 'proposal_submitted'
  | 'proposal_approved'
  | 'proposal_denied';

export interface ActivityEvent {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_level: number;
  event_type: ActivityEventType;
  summary: string;
  revenue_impact_inr: number;
  timestamp: string;
}

// ─── Metrics ────────────────────────────────────────────────────────────────
export interface MetricOverview {
  mrr_inr: number;
  mrr_target_inr: number;
  mrr_delta_wow: number;
  leads_today: number;
  leads_7d_avg: number;
  conv_rate_pct: number;
  conv_rate_delta_pp: number;
  active_agents: number;
  total_agents: number;
  agents_by_level: { l1: number; l2: number; l3: number };
}

export interface MetricDataPoint {
  date: string;
  mrr_inr: number;
  leads_count: number;
  conv_rate_pct: number;
}

export interface AgentRevenueWeek {
  week: string;
  [agent_id: string]: number | string;
}

export interface SpawnKillEvent {
  agent_id: string;
  agent_name: string;
  event_type: 'spawn' | 'kill';
  timestamp: string;
}

// ─── Approvals ──────────────────────────────────────────────────────────────
export interface ApprovalItem {
  id: string;
  task_id: string;
  agent_id: string;
  agent_name: string;
  risk: RiskLevel;
  summary: string;
  proposed_action_summary: string;
  cost_inr: number | null;
  created_at: string;
}

export interface ApprovalFull {
  id: string;
  task_id: string;
  agent_id: string;
  agent_name: string;
  risk: RiskLevel;
  what: string;
  why: string;
  risk_consequence: string;
  proposed_action_payload: Record<string, unknown>;
  cost_inr: number | null;
  created_at: string;
  snoozed_until: string | null;
}

// ─── Skills ─────────────────────────────────────────────────────────────────
export interface SkillPrimitive {
  id: string;
  name: string;
  description: string;
  prompt_fragment: string;
  prompt_fragment_preview: string;
  tools: string[];
  avg_tokens_per_call: number;
  avg_cost_inr_per_call: number;
  avg_quality_score: number;
  usage_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  tags: string[];
}

// ─── Agent Versions ─────────────────────────────────────────────────────────
export interface AgentVersion {
  id: string;
  agent_id: string;
  version: number;
  snapshot_at: string;
  skill_ids: string[];
  change_summary: string;
  proposed_by: string;
  success_rate_pct: number;
  revenue_attributed_inr: number;
  tokens_per_task_avg: number;
  approved_by: string | null;
}

// ─── Tournaments ────────────────────────────────────────────────────────────
export interface JudgeCriterion {
  id: string;
  label: string;
  weight: number;
  description: string;
}

export interface TournamentContestant {
  agent_id: string;
  agent_name: string;
  status: 'waiting' | 'running' | 'done' | 'failed';
  output_tokens_so_far: number;
  final_output: string | null;
  scores: Record<string, number>;
  total_score: number | null;
  cost_inr: number;
}

export interface Tournament {
  id: string;
  title: string;
  task_description: string;
  task_input: Record<string, unknown>;
  contestants: TournamentContestant[];
  judge_criteria: JudgeCriterion[];
  status: 'pending' | 'running' | 'scoring' | 'resolved';
  winner_agent_id: string | null;
  started_at: string | null;
  resolved_at: string | null;
  created_by: string;
}

// ─── Teams ──────────────────────────────────────────────────────────────────
export interface Team {
  id: string;
  name: string;
  purpose: string;
  lead_agent_id: string;
  member_agent_ids: string[];
  created_at: string;
  dissolved_at: string | null;
  aggregate_revenue_inr: number;
  aggregate_success_rate_pct: number;
  task_count: number;
}

// ─── Jobs ───────────────────────────────────────────────────────────────────
export interface Application {
  id: string;
  job_id: string;
  agent_id: string;
  agent_name: string;
  pitch: string;
  skill_match_pct: number;
  applied_at: string;
}

export interface JobPost {
  id: string;
  title: string;
  description: string;
  requirements: string[];
  posted_by: string;
  posted_at: string;
  closes_at: string;
  status: 'open' | 'closed' | 'filled';
  filled_by_agent_id: string | null;
  application_count: number;
  applications: Application[];
}

// ─── Memory ─────────────────────────────────────────────────────────────────
export interface AgentMemory {
  id: string;
  agent_id: string;
  agent_name: string;
  key: string;
  value: string;
  value_preview: string;
  created_at: string;
  last_used_at: string;
  relevance_score: number;
  decay_half_life_days: number;
  is_pinned: boolean;
  promoted_to_skill_id: string | null;
  tags: string[];
}

// ─── Meta Proposals ─────────────────────────────────────────────────────────
export type MetaProposalType =
  | 'evolve_skill'
  | 'spawn_rule_change'
  | 'team_restructure'
  | 'budget_reallocation'
  | 'kill_underperformer'
  | 'promote_agent';

export interface MetaEvidence {
  metric: string;
  before: number;
  after_projected: number;
  data_window_days: number;
}

export interface DiffChunk {
  type: 'added' | 'removed' | 'unchanged';
  text: string;
  annotation: string | null;
}

export interface SkillDiff {
  skill_id: string;
  skill_name: string;
  version_from: number;
  version_to: number;
  chunks: DiffChunk[];
}

export interface MetaProposal {
  id: string;
  proposed_by: string;
  proposal_type: MetaProposalType;
  title: string;
  rationale: string;
  evidence: MetaEvidence[];
  diff?: SkillDiff;
  risk: RiskLevel;
  expected_impact_inr: number;
  status: 'pending' | 'approved' | 'denied' | 'snoozed';
  created_at: string;
  snoozed_until: string | null;
}

export interface MetaLearningSummary {
  proposals_pending: number;
  spawn_rules_proposed_this_week: number;
  avg_quality_delta_pct: number;
  last_proposal_at: string;
}

// ─── Cost ───────────────────────────────────────────────────────────────────
export interface AgentCostSnapshot {
  agent_id: string;
  agent_name: string;
  week: string;
  tokens_input: number;
  tokens_output: number;
  cost_inr: number;
  revenue_attributed_inr: number;
  efficiency: number;
  over_budget: boolean;
}

export interface CostOverview {
  total_spend_inr_this_week: number;
  total_revenue_inr_this_week: number;
  overall_efficiency: number;
  over_budget_agents: string[];
  budget_burn_pct: number;
}

// ─── Mode ───────────────────────────────────────────────────────────────────
export type FounderMode = 'AUTO' | 'REVIEW' | 'MANUAL';

export interface ModeState {
  mode: FounderMode;
  set_by: string;
  set_at: string;
}

import type {
  Agent,
  AgentTask,
  ActivityEvent,
  ApprovalFull,
  MetricOverview,
  MetricDataPoint,
  AgentRevenueWeek,
  SpawnKillEvent,
  SkillPrimitive,
  AgentVersion,
  Tournament,
  Team,
  JobPost,
  AgentMemory,
  MetaProposal,
  MetaLearningSummary,
  AgentCostSnapshot,
  CostOverview,
  ModeState,
  FounderMode,
  TaskFilters,
  AuditLogLine,
} from '@/types';
import {
  mockAgents,
  mockTasks,
  mockApprovals,
  mockMetricOverview,
  mockMetricPoints,
  mockAgentRevenueWeeks,
  mockSpawnKill,
  mockSkills,
  mockAgentVersions,
  mockTournaments,
  mockTeams,
  mockJobs,
  mockMemories,
  mockProposals,
  mockMetaLearning,
  mockCostSnapshots,
  mockCostOverview,
  mockModeState,
  mockAuditLogs,
  mockSkillPreview,
} from './mock';
import { USE_MOCK } from './constants';

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';
const TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? '';

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Helper for fake latency so UI doesn't flash
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function mock<T>(data: T, ms = 150): Promise<T> {
  await sleep(ms);
  // deep clone to avoid mutations leaking across queries
  return JSON.parse(JSON.stringify(data)) as T;
}

// ────────────────────────────────────────────────────────────────────────────
// Public API — swap between mock + real
// ────────────────────────────────────────────────────────────────────────────
export const api = {
  // Agents
  async getAgents(): Promise<Agent[]> {
    if (USE_MOCK) return mock(mockAgents);
    return http<Agent[]>('/agents');
  },
  async getAgent(id: string): Promise<Agent & { recent_tasks: AgentTask[]; audit_log: AuditLogLine[]; skill_preview: string }> {
    if (USE_MOCK) {
      const agent = mockAgents.find((a) => a.id === id);
      if (!agent) throw new Error('not_found');
      return mock({
        ...agent,
        recent_tasks: mockTasks.filter((t) => t.agent_id === id).slice(0, 10),
        audit_log: mockAuditLogs[id] ?? [],
        skill_preview: mockSkillPreview[agent.skill_id] ?? '# No skill preview available',
      });
    }
    return http(`/agents/${id}`);
  },
  async getAgentVersions(id: string): Promise<AgentVersion[]> {
    if (USE_MOCK) return mock(mockAgentVersions[id] ?? []);
    return http(`/agents/${id}/versions`);
  },
  async spawnAgent(payload: {
    parent_id: string;
    name: string;
    skill_id: string;
    level: number;
    description: string;
    inherited_agent_ids?: string[];
    inherited_memory_ids?: string[];
    context_token_budget?: number;
  }): Promise<{ agent_id: string; spawned_at: string }> {
    if (USE_MOCK) return mock({ agent_id: `agt_${Date.now()}`, spawned_at: new Date().toISOString() });
    return http('/agents/spawn', { method: 'POST', body: JSON.stringify(payload) });
  },
  async killAgent(id: string): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return http(`/agents/${id}/kill`, { method: 'POST' });
  },
  async cloneAgent(config: unknown): Promise<{ clone_ids: string[]; tournament_id: string | null }> {
    if (USE_MOCK) return mock({ clone_ids: ['agt_clone_1', 'agt_clone_2'], tournament_id: 'trn_new' });
    return http('/agents/clone', { method: 'POST', body: JSON.stringify(config) });
  },
  async rollbackAgent(id: string, target_version_id: string): Promise<{ rolled_back_at: string }> {
    if (USE_MOCK) return mock({ rolled_back_at: new Date().toISOString() });
    return http(`/agents/${id}/rollback`, { method: 'POST', body: JSON.stringify({ target_version_id }) });
  },
  async bulkKill(threshold: { max_cost_inr_per_week: number; min_revenue_inr_per_week: number }): Promise<{ killed_count: number; killed_agent_ids: string[] }> {
    if (USE_MOCK) return mock({ killed_count: 2, killed_agent_ids: ['agt_content_001', 'agt_data_001'] });
    return http('/agents/bulk-kill', { method: 'POST', body: JSON.stringify(threshold) });
  },

  // Tasks
  async getTasks(filters?: TaskFilters): Promise<{ items: AgentTask[]; total: number }> {
    if (USE_MOCK) {
      let items = mockTasks;
      if (filters?.status?.length) items = items.filter((t) => filters.status!.includes(t.status));
      if (filters?.risk?.length) items = items.filter((t) => filters.risk!.includes(t.risk));
      if (filters?.agent_ids?.length) items = items.filter((t) => filters.agent_ids!.includes(t.agent_id));
      if (filters?.search) {
        const s = filters.search.toLowerCase();
        items = items.filter((t) => t.summary.toLowerCase().includes(s));
      }
      return mock({ items, total: items.length });
    }
    const qs = new URLSearchParams();
    if (filters?.search) qs.set('search', filters.search);
    return http(`/tasks?${qs.toString()}`);
  },
  async approveTask(id: string): Promise<{ approved_at: string }> {
    if (USE_MOCK) return mock({ approved_at: new Date().toISOString() });
    return http(`/tasks/${id}/approve`, { method: 'POST' });
  },
  async denyTask(id: string, reason?: string): Promise<{ denied_at: string }> {
    if (USE_MOCK) return mock({ denied_at: new Date().toISOString() });
    return http(`/tasks/${id}/deny`, { method: 'POST', body: JSON.stringify({ reason }) });
  },
  async snoozeTask(id: string, duration_minutes = 120): Promise<{ snoozed_until: string }> {
    if (USE_MOCK) return mock({ snoozed_until: new Date(Date.now() + duration_minutes * 60_000).toISOString() });
    return http(`/tasks/${id}/snooze`, { method: 'POST', body: JSON.stringify({ duration_minutes }) });
  },
  async batchTasks(ids: string[], action: 'approve' | 'deny', reason?: string): Promise<{ processed: number; failed: string[] }> {
    if (USE_MOCK) return mock({ processed: ids.length, failed: [] });
    return http('/tasks/batch', { method: 'POST', body: JSON.stringify({ ids, action, reason }) });
  },

  // Approvals
  async getApprovals(): Promise<ApprovalFull[]> {
    if (USE_MOCK) return mock(mockApprovals);
    return http('/approvals');
  },

  // Metrics
  async getMetricOverview(): Promise<MetricOverview> {
    if (USE_MOCK) return mock(mockMetricOverview);
    return http('/metrics/overview');
  },
  async getMetrics(): Promise<{
    data_points: MetricDataPoint[];
    agent_revenue: AgentRevenueWeek[];
    spawn_kill_events: SpawnKillEvent[];
    summary: MetricOverview;
  }> {
    if (USE_MOCK) {
      return mock({
        data_points: mockMetricPoints,
        agent_revenue: mockAgentRevenueWeeks,
        spawn_kill_events: mockSpawnKill,
        summary: mockMetricOverview,
      });
    }
    return http('/metrics');
  },
  async getEconomics(): Promise<{ snapshots: AgentCostSnapshot[]; overview: CostOverview }> {
    if (USE_MOCK) return mock({ snapshots: mockCostSnapshots, overview: mockCostOverview });
    return http('/metrics/economics');
  },

  // Skills
  async getSkills(): Promise<SkillPrimitive[]> {
    if (USE_MOCK) return mock(mockSkills);
    return http('/skills');
  },
  async saveSkill(skill: Partial<SkillPrimitive>): Promise<SkillPrimitive> {
    if (USE_MOCK) return mock({ ...mockSkills[0], ...skill } as SkillPrimitive);
    return http('/skills', { method: 'POST', body: JSON.stringify(skill) });
  },

  // Tournaments
  async getTournaments(): Promise<Tournament[]> {
    if (USE_MOCK) return mock(mockTournaments);
    return http('/tournaments');
  },
  async crownWinner(tournamentId: string, winner_agent_id: string): Promise<{ crowned_at: string }> {
    if (USE_MOCK) return mock({ crowned_at: new Date().toISOString() });
    return http(`/tournaments/${tournamentId}/crown`, { method: 'POST', body: JSON.stringify({ winner_agent_id }) });
  },

  // Teams
  async getTeams(): Promise<Team[]> {
    if (USE_MOCK) return mock(mockTeams);
    return http('/teams');
  },

  // Jobs
  async getJobs(): Promise<JobPost[]> {
    if (USE_MOCK) return mock(mockJobs.filter((j) => j.status === 'open'));
    return http('/jobs?status=open');
  },
  async forcePickJob(jobId: string, agent_id: string): Promise<{ hired_at: string; agent_id: string }> {
    if (USE_MOCK) return mock({ hired_at: new Date().toISOString(), agent_id });
    return http(`/jobs/${jobId}/force-pick`, { method: 'POST', body: JSON.stringify({ agent_id }) });
  },

  // Memory
  async getMemories(): Promise<{ items: AgentMemory[]; total: number }> {
    if (USE_MOCK) return mock({ items: mockMemories, total: mockMemories.length });
    return http('/memories');
  },
  async pinMemories(ids: string[]): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return Promise.all(ids.map((id) => http(`/memories/${id}/pin`, { method: 'POST' }))).then(() => undefined);
  },
  async unpinMemories(ids: string[]): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return Promise.all(ids.map((id) => http(`/memories/${id}/unpin`, { method: 'POST' }))).then(() => undefined);
  },
  async deleteMemories(ids: string[]): Promise<{ deleted: number }> {
    if (USE_MOCK) return mock({ deleted: ids.length });
    return http('/memories', { method: 'DELETE', body: JSON.stringify({ ids }) });
  },

  // Proposals
  async getProposals(): Promise<MetaProposal[]> {
    if (USE_MOCK) return mock(mockProposals);
    return http('/proposals').then((r: any) => r.items ?? r);
  },
  async approveProposal(id: string): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return http(`/proposals/${id}/approve`, { method: 'POST' });
  },
  async denyProposal(id: string, reason?: string): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return http(`/proposals/${id}/deny`, { method: 'POST', body: JSON.stringify({ reason }) });
  },
  async snoozeProposal(id: string, duration_minutes = 120): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return http(`/proposals/${id}/snooze`, { method: 'POST', body: JSON.stringify({ duration_minutes }) });
  },
  async requestMoreEvidence(id: string): Promise<void> {
    if (USE_MOCK) return mock(undefined);
    return http(`/proposals/${id}/request-evidence`, { method: 'POST' });
  },
  async getMetaSummary(): Promise<MetaLearningSummary> {
    if (USE_MOCK) return mock(mockMetaLearning);
    return http('/meta/summary');
  },

  // Mode
  async getMode(): Promise<ModeState> {
    if (USE_MOCK) return mock(mockModeState);
    return http('/settings/mode');
  },
  async setMode(mode: FounderMode): Promise<ModeState> {
    if (USE_MOCK) return mock({ ...mockModeState, mode, set_at: new Date().toISOString() });
    return http('/settings/mode', { method: 'PUT', body: JSON.stringify({ mode }) });
  },

  // Misc
  async tick(): Promise<{ tick_started_at: string }> {
    if (USE_MOCK) return mock({ tick_started_at: new Date().toISOString() });
    return http('/meta/tick', { method: 'POST' });
  },
  async healthz(): Promise<{ status: string; version: string; db: string }> {
    if (USE_MOCK) return mock({ status: 'ok', version: 'mock', db: 'connected' });
    return http('/healthz');
  },
};

export type { ActivityEvent };

'use client';

import { useState } from 'react';
import { RefreshCw, Briefcase } from 'lucide-react';
import {
  useAgents,
  useApprovals,
  useApproveTask,
  useDenyTask,
  useJobs,
  useKillAgent,
  useMetaSummary,
  useMetricOverview,
  useTick,
} from '@/hooks';
import { api } from '@/lib/api';
import { MetricTile } from '@/components/molecules/MetricTile';
import { MetaLearningCard } from '@/components/molecules/MetaLearningCard';
import { RevenueCounter } from '@/components/molecules/RevenueCounter';
import { OrgTree } from '@/components/organisms/OrgTree';
import { ActivityFeed } from '@/components/organisms/ActivityFeed';
import { ApprovalsCarousel } from '@/components/organisms/ApprovalsCarousel';
import { AgentDrawer } from '@/components/organisms/AgentDrawer';
import { KillAgentDialog } from '@/components/molecules/KillAgentDialog';
import { SpawnAgentSheet } from '@/components/molecules/SpawnAgentSheet';
import { JobPostCard } from '@/components/molecules/JobPostCard';
import { formatINRShort } from '@/lib/utils';
import type { Agent } from '@/types';
import { MRR_TARGET_INR } from '@/lib/constants';

export default function DashboardPage() {
  const overview = useMetricOverview();
  const agents = useAgents();
  const approvals = useApprovals();
  const meta = useMetaSummary();
  const jobs = useJobs();
  const approve = useApproveTask();
  const deny = useDenyTask();
  const killAgent = useKillAgent();
  const tickMeta = useTick();

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [killTarget, setKillTarget] = useState<Agent | null>(null);
  const [spawnParent, setSpawnParent] = useState<{ id: string; level: number } | null>(null);

  const mrr = overview.data?.mrr_inr ?? 0;
  const target = overview.data?.mrr_target_inr ?? MRR_TARGET_INR;
  const pct = target ? (mrr / target) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Hero metric row — 5 tiles */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-12 md:col-span-4 xl:col-span-3">
          <MetricTile
            label="MRR this month"
            accent
            isLoading={overview.isLoading}
            error={overview.isError}
            value={<RevenueCounter inr={mrr} size="hero" />}
            subtext={
              <span>
                Goal {formatINRShort(target)} · {pct.toFixed(1)}% there ·{' '}
                <span className="text-success font-semibold">
                  +{formatINRShort(overview.data?.mrr_delta_wow ?? 0)}
                </span>{' '}
                wk
              </span>
            }
            progress={{ value: mrr, max: target }}
          />
        </div>
        <div className="col-span-6 md:col-span-2 xl:col-span-2">
          <MetricTile
            label="Leads today"
            isLoading={overview.isLoading}
            error={overview.isError}
            value={<span className="text-2xl font-bold tabular-nums">{overview.data?.leads_today ?? 0}</span>}
            subtext={
              <span className="text-success">
                ↑ +{(overview.data?.leads_today ?? 0) - (overview.data?.leads_7d_avg ?? 0)} vs 7d avg
              </span>
            }
          />
        </div>
        <div className="col-span-6 md:col-span-2 xl:col-span-2">
          <MetricTile
            label="Conv. rate"
            isLoading={overview.isLoading}
            error={overview.isError}
            value={
              <span className="text-2xl font-bold tabular-nums">
                {(overview.data?.conv_rate_pct ?? 0).toFixed(1)}%
              </span>
            }
            subtext={
              <span className="text-success">
                ↑ +{(overview.data?.conv_rate_delta_pp ?? 0).toFixed(1)}pp this week
              </span>
            }
          />
        </div>
        <div className="col-span-6 md:col-span-2 xl:col-span-2">
          <MetricTile
            label="Active agents"
            isLoading={overview.isLoading}
            error={overview.isError}
            value={
              <span className="text-2xl font-bold tabular-nums">
                {overview.data?.active_agents ?? 0} / {overview.data?.total_agents ?? 0}
              </span>
            }
            subtext={
              <span>
                {overview.data?.agents_by_level?.l2 ?? 0} L2 · {overview.data?.agents_by_level?.l3 ?? 0} L3
              </span>
            }
          />
        </div>
        <div className="col-span-6 md:col-span-2 xl:col-span-3">
          <MetaLearningCard summary={meta.data} isLoading={meta.isLoading} />
        </div>
      </section>

      {/* Middle row — Org + Feed */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-12 xl:col-span-8">
          <div className="rounded-2xl border border-border bg-surface">
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <h3 className="text-[11px] font-bold uppercase tracking-widest text-text-muted">Company org</h3>
              <button
                onClick={() => tickMeta.mutate()}
                disabled={tickMeta.isPending}
                className="flex items-center gap-1 px-2 py-1 text-xs text-text-muted hover:text-text rounded-md border border-border hover:border-accent/40"
              >
                <RefreshCw size={12} className={tickMeta.isPending ? 'animate-spin' : ''} />
                Tick
              </button>
            </div>
            <div className="h-[420px] p-4">
              {agents.isLoading ? (
                <div className="h-full flex items-center justify-center text-text-muted text-sm">
                  Loading agents…
                </div>
              ) : agents.data && agents.data.length > 0 ? (
                <OrgTree
                  agents={agents.data.map((a) => ({
                    id: a.id,
                    name: a.name,
                    level: a.level,
                    status: a.status,
                    parent_id: a.parent_id,
                    current_task_summary: a.current_task_summary,
                    crown: a.crown,
                    killed_at: a.killed_at,
                  }))}
                  onNodeClick={setSelectedAgentId}
                />
              ) : (
                <div className="h-full flex flex-col items-center justify-center gap-3 text-center">
                  <div className="text-sm text-text-muted">
                    No agents running. Spawn the Meta Agent to begin.
                  </div>
                  <button className="px-3 py-1.5 rounded-md bg-accent text-white text-xs font-medium">
                    Spawn Meta Agent
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="col-span-12 xl:col-span-4 space-y-4">
          <ActivityFeed />
          <div className="rounded-2xl border border-border bg-surface">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <h3 className="text-[11px] font-bold uppercase tracking-widest text-text-muted flex items-center gap-1.5">
                <Briefcase size={12} />
                Open jobs ({jobs.data?.length ?? 0})
              </h3>
              <button className="text-[11px] text-accent hover:underline">Post job +</button>
            </div>
            <div className="p-3 space-y-2">
              {jobs.isLoading ? (
                <div className="text-xs text-text-muted p-2">Loading jobs…</div>
              ) : jobs.data && jobs.data.length > 0 ? (
                jobs.data.map((j) => (
                  <JobPostCard
                    key={j.id}
                    job={j}
                    onForcePick={(jobId, agentId) => api.forcePickJob(jobId, agentId)}
                  />
                ))
              ) : (
                <div className="text-xs text-text-muted p-2">No open jobs right now.</div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Approvals carousel */}
      <section>
        {approvals.isLoading ? (
          <div className="rounded-2xl border border-border bg-surface p-5 text-sm text-text-muted">
            Loading approvals…
          </div>
        ) : approvals.isError ? (
          <div className="rounded-2xl border border-danger/30 bg-surface p-5 text-sm text-danger">
            Failed to load approvals.
          </div>
        ) : (
          <ApprovalsCarousel
            approvals={approvals.data ?? []}
            onApprove={(id) => {
              const a = approvals.data?.find((x) => x.id === id);
              if (a) approve.mutate(a.task_id);
            }}
            onDeny={(id) => {
              const a = approvals.data?.find((x) => x.id === id);
              if (a) deny.mutate({ id: a.task_id });
            }}
          />
        )}
      </section>

      <AgentDrawer
        agentId={selectedAgentId}
        open={!!selectedAgentId}
        onClose={() => setSelectedAgentId(null)}
        onKill={(a) => setKillTarget(a)}
        onSpawnChild={(id, lvl) => setSpawnParent({ id, level: lvl })}
      />
      <KillAgentDialog
        agent={killTarget}
        open={!!killTarget}
        onConfirm={() => {
          if (killTarget) killAgent.mutate(killTarget.id);
          setKillTarget(null);
        }}
        onCancel={() => setKillTarget(null)}
      />
      <SpawnAgentSheet
        parentId={spawnParent?.id ?? null}
        parentLevel={spawnParent?.level ?? 0}
        open={!!spawnParent}
        onClose={() => setSpawnParent(null)}
        onSpawn={async (payload) => {
          await api.spawnAgent(payload);
          setSpawnParent(null);
        }}
      />
    </div>
  );
}

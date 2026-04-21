'use client';

import { useState } from 'react';
import { LayoutGrid, Network, Users } from 'lucide-react';
import { useAgents, useKillAgent, useTeams } from '@/hooks';
import { AgentCard } from '@/components/molecules/AgentCard';
import { OrgTree } from '@/components/organisms/OrgTree';
import { AgentDrawer } from '@/components/organisms/AgentDrawer';
import { KillAgentDialog } from '@/components/molecules/KillAgentDialog';
import { SpawnAgentSheet } from '@/components/molecules/SpawnAgentSheet';
import { CloneWizardSheet } from '@/components/organisms/CloneWizardSheet';
import { cn, formatINRShort } from '@/lib/utils';
import type { Agent } from '@/types';
import { api } from '@/lib/api';

type Mode = 'grid' | 'tree' | 'teams';

export default function AgentsPage() {
  const [mode, setMode] = useState<Mode>('grid');
  const agents = useAgents();
  const teams = useTeams();
  const kill = useKillAgent();
  const [selected, setSelected] = useState<string | null>(null);
  const [killTarget, setKillTarget] = useState<Agent | null>(null);
  const [spawnParent, setSpawnParent] = useState<{ id: string; level: number } | null>(null);
  const [cloneTarget, setCloneTarget] = useState<Agent | null>(null);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-text">Agents</h1>
        <div className="inline-flex items-center rounded-lg bg-elevated border border-border p-0.5 gap-0.5">
          <ModeBtn active={mode === 'grid'} onClick={() => setMode('grid')} icon={<LayoutGrid size={12} />}>
            Individuals
          </ModeBtn>
          <ModeBtn active={mode === 'teams'} onClick={() => setMode('teams')} icon={<Users size={12} />}>
            Teams
          </ModeBtn>
          <ModeBtn active={mode === 'tree'} onClick={() => setMode('tree')} icon={<Network size={12} />}>
            Org tree
          </ModeBtn>
        </div>
      </div>

      {agents.isLoading && <SkeletonGrid />}
      {agents.data && agents.data.length === 0 && (
        <EmptyState>No agents running. Spawn the Meta Agent from the dashboard.</EmptyState>
      )}

      {mode === 'grid' && agents.data && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {agents.data.map((a) => (
            <AgentCard
              key={a.id}
              agent={a}
              onView={setSelected}
              onKill={setKillTarget}
              onClone={setCloneTarget}
            />
          ))}
        </div>
      )}

      {mode === 'tree' && agents.data && (
        <div className="rounded-2xl border border-border bg-surface p-4 h-[600px]">
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
            onNodeClick={setSelected}
          />
        </div>
      )}

      {mode === 'teams' && teams.data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {teams.data.map((t) => (
            <div key={t.id} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-text">{t.name}</h3>
                <button className="text-xs text-text-muted hover:text-text">Expand ▾</button>
              </div>
              <p className="text-xs text-text-muted mb-2">{t.purpose}</p>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[11px] text-text-faint">Lead:</span>
                <span className="text-xs font-medium text-text">
                  {agents.data?.find((a) => a.id === t.lead_agent_id)?.name ?? '—'}
                </span>
              </div>
              <div className="flex -space-x-2 mb-3">
                {t.member_agent_ids.map((id) => {
                  const a = agents.data?.find((x) => x.id === id);
                  return (
                    <div
                      key={id}
                      className="w-7 h-7 rounded-full border-2 border-surface bg-accent-dim flex items-center justify-center text-[10px] font-bold text-accent"
                      title={a?.name}
                    >
                      {a?.name.charAt(0) ?? '?'}
                    </div>
                  );
                })}
              </div>
              <dl className="grid grid-cols-3 gap-2 text-xs text-text-muted">
                <div>
                  <dt className="text-text-faint">Revenue</dt>
                  <dd className="text-text font-semibold tabular-nums">{formatINRShort(t.aggregate_revenue_inr)}</dd>
                </div>
                <div>
                  <dt className="text-text-faint">Success</dt>
                  <dd className="text-text font-semibold tabular-nums">{t.aggregate_success_rate_pct.toFixed(1)}%</dd>
                </div>
                <div>
                  <dt className="text-text-faint">Tasks</dt>
                  <dd className="text-text font-semibold tabular-nums">{t.task_count}</dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      )}

      <AgentDrawer
        agentId={selected}
        open={!!selected}
        onClose={() => setSelected(null)}
        onKill={(a) => setKillTarget(a)}
        onSpawnChild={(id, lvl) => setSpawnParent({ id, level: lvl })}
      />
      <KillAgentDialog
        agent={killTarget}
        open={!!killTarget}
        onConfirm={() => {
          if (killTarget) kill.mutate(killTarget.id);
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
      <CloneWizardSheet
        sourceAgent={cloneTarget}
        open={!!cloneTarget}
        onClose={() => setCloneTarget(null)}
        onSubmit={async (cfg) => {
          await api.cloneAgent(cfg);
          setCloneTarget(null);
        }}
      />
    </div>
  );
}

function ModeBtn({
  active,
  onClick,
  children,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  icon: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors',
        active ? 'bg-accent text-white' : 'text-text-muted hover:text-text'
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="rounded-xl border border-border bg-surface p-4 animate-pulse">
          <div className="h-4 w-24 bg-elevated rounded mb-3" />
          <div className="h-3 w-16 bg-elevated rounded mb-4" />
          <div className="h-10 w-full bg-elevated rounded mb-4" />
          <div className="h-3 w-full bg-elevated rounded" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface p-10 text-center text-sm text-text-muted">
      {children}
    </div>
  );
}

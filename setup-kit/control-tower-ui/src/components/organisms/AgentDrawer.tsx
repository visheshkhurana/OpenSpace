'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { X, GitBranch, Skull } from 'lucide-react';
import { useAgent, useAgentVersions } from '@/hooks';
import { LevelChip } from '@/components/atoms/LevelChip';
import { StatusDot } from '@/components/atoms/StatusDot';
import { SkillDiffView } from '@/components/molecules/SkillDiffView';
import { formatINRShort, formatTimeAgo } from '@/lib/utils';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { Agent } from '@/types';

type Tab = 'history' | 'versions' | 'skills' | 'cost';

export function AgentDrawer({
  agentId,
  open,
  onClose,
  onKill,
  onSpawnChild,
}: {
  agentId: string | null;
  open: boolean;
  onClose: () => void;
  onKill: (a: Agent) => void;
  onSpawnChild: (parentId: string, parentLevel: number) => void;
}) {
  const { data: agent, isLoading } = useAgent(agentId);
  const { data: versions } = useAgentVersions(agentId);
  const [tab, setTab] = useState<Tab>('history');

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="absolute right-0 top-0 bottom-0 w-full sm:w-[540px] bg-surface border-l border-border flex flex-col"
            role="dialog"
            aria-label="Agent detail"
          >
            <div className="flex items-center justify-between p-5 border-b border-border">
              {agent ? (
                <div className="flex items-center gap-2 min-w-0">
                  <StatusDot status={agent.status} />
                  <h2 className="text-lg font-semibold text-text truncate">{agent.name}</h2>
                  <LevelChip level={agent.level} />
                  <span className="text-xs font-mono text-text-faint">v{agent.version}</span>
                </div>
              ) : (
                <div className="h-6 w-40 rounded bg-elevated animate-pulse" />
              )}
              <button onClick={onClose} className="text-text-muted hover:text-text" aria-label="Close">
                <X size={20} />
              </button>
            </div>

            <div className="flex items-center gap-1 px-5 py-2 border-b border-border">
              {(['history', 'versions', 'skills', 'cost'] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    'px-2.5 py-1 text-xs font-medium rounded-md capitalize transition-colors',
                    tab === t ? 'bg-accent-dim text-accent' : 'text-text-muted hover:text-text'
                  )}
                >
                  {t}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {isLoading && <div className="text-sm text-text-muted">Loading…</div>}

              {agent && tab === 'history' && (
                <>
                  <Section title="Current task">
                    {agent.current_task_summary ? (
                      <div className="text-sm text-text leading-relaxed">{agent.current_task_summary}</div>
                    ) : (
                      <div className="text-sm text-text-faint italic">Idle — no active task.</div>
                    )}
                  </Section>
                  <Section title="Stats">
                    <dl className="grid grid-cols-2 gap-3 text-sm">
                      <Stat label="Revenue attributed" value={formatINRShort(agent.revenue_attributed_inr)} />
                      <Stat label="Success rate" value={`${agent.success_rate_pct.toFixed(1)}%`} />
                      <Stat label="Tasks (total)" value={`${agent.task_count_total}`} />
                      <Stat label="Tasks (success)" value={`${agent.task_count_success}`} />
                      <Stat label="Spawned" value={formatTimeAgo(agent.spawned_at)} />
                      <Stat label="Cost" value={formatINRShort(agent.cost_to_date_inr)} />
                    </dl>
                  </Section>
                  <Section title="Skill preview">
                    <pre className="text-[11px] font-mono text-text-muted bg-bg border border-border rounded-md p-3 overflow-auto max-h-40 whitespace-pre-wrap">
                      {agent.skill_preview}
                    </pre>
                  </Section>
                  <Section title="Recent tasks">
                    {agent.recent_tasks.length === 0 ? (
                      <div className="text-sm text-text-faint italic">No tasks recorded yet.</div>
                    ) : (
                      <div className="space-y-1.5">
                        {agent.recent_tasks.map((t) => (
                          <div key={t.id} className="flex items-center justify-between text-xs bg-bg rounded-md px-2 py-1.5 border border-border">
                            <span className="font-mono text-text-faint">#{t.id.slice(-6)}</span>
                            <span className="flex-1 mx-2 truncate text-text-muted">{t.summary}</span>
                            <span className="text-text-faint">{formatTimeAgo(t.created_at)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Section>
                  <Section title="Audit log tail">
                    {agent.audit_log.length === 0 ? (
                      <div className="text-sm text-text-faint italic">No log lines.</div>
                    ) : (
                      <pre className="text-[11px] font-mono text-text-muted bg-bg border border-border rounded-md p-3 overflow-auto max-h-40 whitespace-pre-wrap">
                        {agent.audit_log
                          .map((l) => `[${new Date(l.ts).toISOString()}] ${l.level} ${l.message}`)
                          .join('\n')}
                      </pre>
                    )}
                  </Section>
                </>
              )}

              {agent && tab === 'versions' && (
                <div className="relative pl-5">
                  <div className="absolute left-1.5 top-0 bottom-0 w-0.5 bg-border" />
                  {versions && versions.length > 0 ? (
                    versions.map((v) => (
                      <div key={v.id} className="relative mb-6">
                        <div
                          className={cn(
                            'absolute -left-[14px] top-1.5 w-3 h-3 rounded-full border-2 border-surface',
                            v.version === agent.version ? 'bg-accent' : 'bg-border'
                          )}
                        />
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-text text-sm">v{v.version}</span>
                          {v.version === agent.version && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-accent-dim text-accent rounded-md">
                              current
                            </span>
                          )}
                          <span className="text-[11px] text-text-faint">
                            {new Date(v.snapshot_at).toLocaleDateString()} · by {v.proposed_by}
                          </span>
                        </div>
                        <p className="mt-1 text-[13px] italic text-text-muted leading-snug">
                          {v.change_summary}
                        </p>
                        <div className="mt-1 text-[11px] text-text-muted">
                          Success: {v.success_rate_pct}% · Revenue: {formatINRShort(v.revenue_attributed_inr)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-text-muted italic">No version history yet.</div>
                  )}
                </div>
              )}

              {agent && tab === 'skills' && (
                <div>
                  <div className="grid grid-cols-1 gap-2">
                    {agent.skills.map((s) => (
                      <div key={s} className="rounded-md border border-border p-3 bg-bg flex items-center justify-between">
                        <span className="font-mono text-sm text-text">{s}</span>
                        <span className="text-[11px] text-text-faint">active</span>
                      </div>
                    ))}
                  </div>
                  <button className="mt-3 w-full py-2 rounded-md border border-dashed border-border text-xs text-text-muted hover:text-text hover:border-text-muted">
                    + Attach skill
                  </button>
                </div>
              )}

              {agent && tab === 'cost' && (
                <div className="space-y-3">
                  <div className="text-sm text-text-muted">
                    This week:{' '}
                    <span className="text-text font-semibold tabular-nums">
                      ₹{agent.cost_to_date_inr.toLocaleString('en-IN')}
                    </span>{' '}
                    · Budget:{' '}
                    <span className="text-text font-semibold tabular-nums">
                      {Math.round((agent.tokens_used_this_week / agent.token_budget_weekly) * 100)}% used
                    </span>
                  </div>
                  <div>
                    <div className="h-2 rounded-full bg-elevated overflow-hidden">
                      <div
                        className="h-full bg-accent"
                        style={{
                          width: `${Math.min(100, (agent.tokens_used_this_week / agent.token_budget_weekly) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <Stat label="Tokens this week" value={agent.tokens_used_this_week.toLocaleString('en-IN')} />
                    <Stat label="Budget (weekly)" value={agent.token_budget_weekly.toLocaleString('en-IN')} />
                  </dl>
                </div>
              )}
            </div>

            {agent && (
              <div className="border-t border-border p-5 flex items-center gap-2">
                <button
                  onClick={() => onSpawnChild(agent.id, agent.level)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent-dim text-accent border border-accent/20 text-xs font-medium hover:bg-accent/20"
                >
                  <GitBranch size={12} />
                  Spawn child
                </button>
                <div className="ml-auto">
                  <button
                    onClick={() => onKill(agent)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-danger/30 text-danger text-xs font-medium hover:bg-danger/10"
                  >
                    <Skull size={12} />
                    Kill
                  </button>
                </div>
              </div>
            )}
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-2">{title}</div>
      {children}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-bg border border-border px-3 py-2">
      <div className="text-[11px] text-text-faint">{label}</div>
      <div className="mt-0.5 text-sm font-semibold text-text tabular-nums">{value}</div>
    </div>
  );
}

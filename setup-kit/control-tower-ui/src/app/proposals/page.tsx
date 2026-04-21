'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, AlertTriangle, CheckCircle2, XCircle, Clock, FileQuestion } from 'lucide-react';
import { useProposals } from '@/hooks';
import { api } from '@/lib/api';
import { SkillDiffView } from '@/components/molecules/SkillDiffView';
import { RiskBadge } from '@/components/atoms/RiskBadge';
import { cn, formatINRShort, formatTimeAgo } from '@/lib/utils';
import { useQueryClient } from '@tanstack/react-query';

export default function ProposalsPage() {
  const { data, isLoading, isError, refetch } = useProposals();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const qc = useQueryClient();

  const invalidate = () => qc.invalidateQueries({ queryKey: ['proposals'] });

  return (
    <div className="space-y-4" style={{ backgroundColor: '#0D0F14' }}>
      <div>
        <h1 className="text-2xl font-bold">Proposals</h1>
        <p className="text-xs text-text-muted mt-0.5">
          Meta-level evolutions from the MetaLearningAgent — not task approvals. Higher stakes.
        </p>
      </div>

      {isLoading && (
        <div className="rounded-xl border border-border bg-surface p-10 text-center text-sm text-text-muted">
          Loading proposals…
        </div>
      )}
      {isError && (
        <div className="rounded-xl border border-danger/30 bg-surface p-6 text-sm text-danger">
          Failed to load proposals.
        </div>
      )}
      {!isLoading && data && data.length === 0 && (
        <div className="rounded-xl border border-dashed border-border bg-surface p-12 text-center text-sm text-text-muted">
          No proposals pending. MetaLearningAgent is quiet.
        </div>
      )}

      <AnimatePresence>
        {data?.map((p) => {
          const e = expanded[p.id] ?? false;
          return (
            <motion.div
              layout
              key={p.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
              className="rounded-xl border border-border bg-surface p-5"
              style={{ borderLeft: '3px solid #7C5CFF' }}
            >
              <div className="flex items-center gap-2 flex-wrap mb-3">
                <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent-dim text-accent border border-accent/20 uppercase tracking-wider">
                  <Cpu size={10} />
                  Proposal
                </span>
                <RiskBadge risk={p.risk} />
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-elevated text-text-muted uppercase tracking-wider">
                  {p.proposal_type.replace(/_/g, ' ')}
                </span>
                <span className="text-xs text-text-muted">· {p.proposed_by}</span>
                <span className="text-xs text-text-faint ml-auto">{formatTimeAgo(p.created_at)}</span>
              </div>

              <h3 className="text-base font-semibold text-text mb-2">{p.title}</h3>

              <div className="mb-3">
                <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1">
                  Rationale
                </div>
                <p className="text-sm text-text-muted leading-relaxed">{p.rationale}</p>
              </div>

              <div className="mb-3">
                <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1">
                  Evidence
                </div>
                <div className="space-y-1">
                  {p.evidence.map((ev, i) => (
                    <div key={i} className="flex items-center gap-3 text-xs font-mono text-text-muted">
                      <span className="w-40 text-text">{ev.metric}</span>
                      <span className="tabular-nums">
                        {ev.before} → {ev.after_projected}
                      </span>
                      <span className="text-success">
                        +{(ev.after_projected - ev.before).toFixed(1)}pp
                      </span>
                      <span className="text-text-faint">· {ev.data_window_days}d window</span>
                    </div>
                  ))}
                  <div className="pt-1 text-xs">
                    <span className="text-text-muted">Expected revenue impact: </span>
                    <span className="text-success font-semibold">
                      +{formatINRShort(p.expected_impact_inr)} / month
                    </span>
                  </div>
                </div>
              </div>

              {p.diff && (
                <div className="mb-3">
                  <button
                    onClick={() => setExpanded((prev) => ({ ...prev, [p.id]: !e }))}
                    className="text-xs text-accent hover:underline"
                  >
                    {e ? '▾' : '▸'} Skill diff — v{p.diff.version_from} → v{p.diff.version_to}
                  </button>
                  {e && (
                    <div className="mt-2">
                      <SkillDiffView diff={p.diff} />
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2 pt-2">
                <button
                  onClick={async () => {
                    await api.approveProposal(p.id);
                    invalidate();
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-success/15 text-success border border-success/20 text-sm font-medium hover:bg-success/25"
                >
                  <CheckCircle2 size={14} />
                  Approve
                  <span className="text-success/50 text-[10px]">A</span>
                </button>
                <button
                  onClick={async () => {
                    await api.denyProposal(p.id);
                    invalidate();
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-danger/15 text-danger border border-danger/20 text-sm font-medium hover:bg-danger/25"
                >
                  <XCircle size={14} />
                  Deny
                  <span className="text-danger/50 text-[10px]">D</span>
                </button>
                <button
                  onClick={async () => {
                    await api.snoozeProposal(p.id);
                    invalidate();
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-elevated text-text-muted border border-border text-sm font-medium hover:bg-border/50"
                >
                  <Clock size={14} />
                  Snooze 2h
                </button>
                <button
                  onClick={() => api.requestMoreEvidence(p.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-text-muted hover:text-text text-sm ml-auto"
                >
                  <FileQuestion size={14} />
                  Request more evidence
                </button>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

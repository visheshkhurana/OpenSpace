'use client';

import { motion } from 'framer-motion';
import { Skull, ChevronRight } from 'lucide-react';
import { LevelChip } from '@/components/atoms/LevelChip';
import { StatusDot } from '@/components/atoms/StatusDot';
import { cn, formatINRShort } from '@/lib/utils';
import type { Agent } from '@/types';

interface AgentCardProps {
  agent: Agent;
  onView: (id: string) => void;
  onKill: (agent: Agent) => void;
  onClone?: (agent: Agent) => void;
}

export function AgentCard({ agent, onView, onKill, onClone }: AgentCardProps) {
  const killed = agent.status === 'killed';
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: killed ? 0.6 : 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn(
        'rounded-xl border bg-surface p-4 transition-all',
        agent.crown ? 'border-warn/40 shadow-[0_0_16px_-4px_rgba(245,158,11,0.3)]' : 'border-border hover:border-border/70'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <StatusDot status={agent.status} />
          <span className="font-semibold text-text text-sm">{agent.name}</span>
          {agent.crown && <span title="Crowned" className="text-warn">👑</span>}
        </div>
        <LevelChip level={agent.level} />
      </div>
      <div className="text-[11px] uppercase tracking-wider text-text-faint">{agent.status}</div>
      <div className="my-3 h-px bg-border" />
      <p className="text-[13px] text-text-muted min-h-[36px] leading-snug">
        {agent.current_task_summary ?? <span className="text-text-faint italic">Idle — no active task.</span>}
      </p>
      <div className="my-3 h-px bg-border" />
      <dl className="space-y-1 text-xs">
        <Row label="Revenue" value={formatINRShort(agent.revenue_attributed_inr)} />
        <Row label="Success" value={`${agent.success_rate_pct.toFixed(1)}%`} />
        <Row label="Version" value={`v${agent.version}`} />
        <Row label="Cost wk" value={formatINRShort(agent.cost_to_date_inr)} />
      </dl>
      <div className="mt-4 flex items-center justify-between gap-2">
        <button
          disabled={killed}
          onClick={() => onKill(agent)}
          className="px-2.5 py-1 text-xs font-medium text-danger hover:bg-danger/10 rounded-md disabled:opacity-40"
        >
          Kill
        </button>
        <div className="flex items-center gap-1">
          {onClone && (
            <button
              onClick={() => onClone(agent)}
              className="px-2.5 py-1 text-xs font-medium text-text-muted hover:text-text rounded-md"
            >
              Clone
            </button>
          )}
          <button
            onClick={() => onView(agent.id)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-accent-dim text-accent border border-accent/20 rounded-md hover:bg-accent/20"
          >
            View
            <ChevronRight size={12} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-text-faint">{label}</dt>
      <dd className="text-text tabular-nums">{value}</dd>
    </div>
  );
}

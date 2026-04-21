'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, CheckCircle2, XCircle, Clock, ChevronDown } from 'lucide-react';
import { cn, formatINRShort } from '@/lib/utils';
import type { ApprovalFull } from '@/types';

interface ApprovalCardProps {
  approval: ApprovalFull;
  focused?: boolean;
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
  onSnooze: (id: string) => void;
  exitDirection?: 'approve' | 'deny' | null;
}

const RISK_CONFIG = {
  HIGH: { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/30', icon: AlertTriangle },
  MEDIUM: { bg: 'bg-warn/10', text: 'text-warn', border: 'border-warn/30', icon: AlertTriangle },
  LOW: { bg: 'bg-success/10', text: 'text-success', border: 'border-success/30', icon: CheckCircle2 },
};

export function ApprovalCard({
  approval,
  focused = false,
  onApprove,
  onDeny,
  onSnooze,
  exitDirection = null,
}: ApprovalCardProps) {
  const [jsonExpanded, setJsonExpanded] = useState(false);
  const risk = RISK_CONFIG[approval.risk];
  const RiskIcon = risk.icon;

  const exitVariants = {
    approve: { x: 120, opacity: 0, transition: { duration: 0.25 } },
    deny: { x: -120, opacity: 0, transition: { duration: 0.25 } },
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={exitDirection ? exitVariants[exitDirection] : { opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0, transition: { duration: 0.2 } }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        'rounded-xl border p-4 bg-surface transition-all duration-150',
        focused ? 'border-accent/60 ring-1 ring-accent/30' : 'border-border'
      )}
      tabIndex={0}
      aria-label={`Approval: ${approval.what}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border tracking-wide',
              risk.bg,
              risk.text,
              risk.border
            )}
          >
            <RiskIcon size={10} />
            {approval.risk}
          </span>
          <span className="text-sm font-medium text-text">{approval.agent_name}</span>
          <span className="text-xs text-text-faint font-mono">#{approval.task_id.slice(-6)}</span>
        </div>
        {approval.cost_inr !== null && (
          <span className="text-xs font-semibold text-warn bg-warn/10 px-2 py-0.5 rounded-full">
            {formatINRShort(approval.cost_inr)}
          </span>
        )}
      </div>

      <div className="space-y-1.5 mb-3">
        <div className="flex gap-2 text-sm">
          <span className="text-text-faint uppercase text-[11px] font-bold w-10 flex-shrink-0 pt-0.5">WHAT</span>
          <span className="text-text">{approval.what}</span>
        </div>
        <div className="flex gap-2 text-sm">
          <span className="text-text-faint uppercase text-[11px] font-bold w-10 flex-shrink-0 pt-0.5">WHY</span>
          <span className="text-text-muted">{approval.why}</span>
        </div>
        <div className="flex gap-2 text-sm">
          <span className="text-text-faint uppercase text-[11px] font-bold w-10 flex-shrink-0 pt-0.5">RISK</span>
          <span className="text-text-muted">{approval.risk_consequence}</span>
        </div>
      </div>

      <div className="mb-3">
        <button
          onClick={() => setJsonExpanded(!jsonExpanded)}
          className="flex items-center gap-1 text-[12px] text-text-faint hover:text-text-muted transition-colors"
        >
          <motion.span animate={{ rotate: jsonExpanded ? 0 : -90 }} transition={{ duration: 0.15 }}>
            <ChevronDown size={12} />
          </motion.span>
          Proposed Action Payload
        </button>
        <AnimatePresence>
          {jsonExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <pre className="mt-2 p-3 rounded-lg bg-bg text-[11px] font-mono text-text-muted border border-border overflow-x-auto leading-relaxed">
                {JSON.stringify(approval.proposed_action_payload, null, 2)}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => onApprove(approval.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/15 text-success border border-success/20 text-sm font-medium hover:bg-success/25 transition-colors"
        >
          <CheckCircle2 size={14} />
          Approve
          <span className="text-success/50 text-[10px] ml-0.5">A</span>
        </button>
        <button
          onClick={() => onDeny(approval.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger/15 text-danger border border-danger/20 text-sm font-medium hover:bg-danger/25 transition-colors"
        >
          <XCircle size={14} />
          Deny
          <span className="text-danger/50 text-[10px] ml-0.5">D</span>
        </button>
        <button
          onClick={() => onSnooze(approval.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-elevated text-text-muted border border-border text-sm font-medium hover:bg-border/50 transition-colors"
        >
          <Clock size={14} />
          Snooze 2h
          <span className="text-text-faint text-[10px] ml-0.5">S</span>
        </button>
      </div>
    </motion.div>
  );
}

'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { X, CheckCircle2, XCircle } from 'lucide-react';
import type { AgentTask } from '@/types';
import { RiskBadge } from '@/components/atoms/RiskBadge';
import { UrgencyDots } from '@/components/atoms/UrgencyDots';
import { MonoBlock } from '@/components/atoms/MonoBlock';
import { formatINRShort, formatTimeAgo } from '@/lib/utils';

export function TaskDrawer({
  task,
  open,
  onClose,
  onApprove,
  onDeny,
}: {
  task: AgentTask | null;
  open: boolean;
  onClose: () => void;
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
}) {
  return (
    <AnimatePresence>
      {open && task && (
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
          >
            <div className="flex items-center justify-between p-5 border-b border-border">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-text">Task</h2>
                <span className="font-mono text-xs text-text-faint">#{task.id}</span>
                <RiskBadge risk={task.risk} />
              </div>
              <button onClick={onClose} className="text-text-muted hover:text-text">
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1">Summary</div>
                <p className="text-sm text-text leading-relaxed">{task.summary}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <Stat label="Agent" value={task.agent_name ?? task.agent_id} />
                <Stat label="Status" value={task.status} />
                <Stat label="Revenue impact" value={formatINRShort(task.revenue_impact_inr)} />
                <Stat label="Urgency">
                  <UrgencyDots urgency={task.urgency} />
                </Stat>
                <Stat label="Created" value={formatTimeAgo(task.created_at)} />
                <Stat label="Completed" value={task.completed_at ? formatTimeAgo(task.completed_at) : '—'} />
              </div>

              <MonoBlock label="Input payload" code={task.input_payload} collapsed={false} />
              <MonoBlock label="Proposed action" code={task.proposed_action} collapsed={false} />
              <MonoBlock label="Output" code={task.output_payload} collapsed={true} />
            </div>

            {task.status === 'approval_required' && (
              <div className="border-t border-border p-5 flex items-center gap-2">
                <button
                  onClick={() => onApprove(task.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-success/15 text-success border border-success/20 text-sm font-medium hover:bg-success/25"
                >
                  <CheckCircle2 size={14} />
                  Approve
                </button>
                <button
                  onClick={() => onDeny(task.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-danger/15 text-danger border border-danger/20 text-sm font-medium hover:bg-danger/25"
                >
                  <XCircle size={14} />
                  Deny
                </button>
              </div>
            )}
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Stat({
  label,
  value,
  children,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-md bg-bg border border-border px-3 py-2">
      <div className="text-[11px] text-text-faint">{label}</div>
      <div className="mt-0.5 text-sm font-semibold text-text tabular-nums">{children ?? value}</div>
    </div>
  );
}

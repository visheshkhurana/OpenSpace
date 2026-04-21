'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useApprovals, useApproveTask, useDenyTask, useSnoozeTask } from '@/hooks';
import { ApprovalCard } from '@/components/molecules/ApprovalCard';
import { cn } from '@/lib/utils';
import type { ApprovalFull, RiskLevel } from '@/types';

type Filter = 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'SNOOZED';

const RISK_ORDER: Record<RiskLevel, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

export default function ApprovalsPage() {
  const { data, isLoading, isError } = useApprovals();
  const approve = useApproveTask();
  const deny = useDenyTask();
  const snooze = useSnoozeTask();

  const [filter, setFilter] = useState<Filter>('ALL');
  const [focused, setFocused] = useState(0);
  const [exiting, setExiting] = useState<Record<string, 'approve' | 'deny'>>({});
  const [helpOpen, setHelpOpen] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const items: ApprovalFull[] = (data ?? [])
    .filter((a) => {
      if (filter === 'ALL') return true;
      if (filter === 'SNOOZED') return !!a.snoozed_until;
      return a.risk === filter;
    })
    .sort((a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk]);

  const fireApprove = (app: ApprovalFull) => {
    setExiting((p) => ({ ...p, [app.id]: 'approve' }));
    setTimeout(() => approve.mutate(app.task_id), 200);
  };
  const fireDeny = (app: ApprovalFull) => {
    setExiting((p) => ({ ...p, [app.id]: 'deny' }));
    setTimeout(() => deny.mutate({ id: app.task_id }), 200);
  };
  const fireSnooze = (app: ApprovalFull) => {
    snooze.mutate(app.task_id);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (helpOpen && e.key === 'Escape') {
        setHelpOpen(false);
        return;
      }
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      const current = items[focused];
      switch (e.key.toLowerCase()) {
        case 'j':
          setFocused((f) => Math.min(f + 1, items.length - 1));
          e.preventDefault();
          break;
        case 'k':
          setFocused((f) => Math.max(f - 1, 0));
          e.preventDefault();
          break;
        case 'a':
          if (current) {
            fireApprove(current);
            e.preventDefault();
          }
          break;
        case 'd':
          if (current) {
            fireDeny(current);
            e.preventDefault();
          }
          break;
        case 's':
          if (current) {
            fireSnooze(current);
            e.preventDefault();
          }
          break;
        case '?':
          setHelpOpen((v) => !v);
          e.preventDefault();
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, focused, helpOpen]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Approvals</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Hotkeys: <kbd className="font-mono">J</kbd>/<kbd className="font-mono">K</kbd> navigate ·{' '}
            <kbd className="font-mono">A</kbd> approve · <kbd className="font-mono">D</kbd> deny ·{' '}
            <kbd className="font-mono">S</kbd> snooze · <kbd className="font-mono">?</kbd> help
          </p>
        </div>
        <div className="inline-flex items-center rounded-lg bg-elevated border border-border p-0.5 gap-0.5">
          {(['ALL', 'HIGH', 'MEDIUM', 'LOW', 'SNOOZED'] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'px-2.5 py-1 text-xs font-medium rounded-md',
                filter === f ? 'bg-accent text-white' : 'text-text-muted hover:text-text'
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div ref={listRef} className="space-y-3">
        {isLoading && (
          <div className="rounded-xl border border-border bg-surface p-10 text-center text-sm text-text-muted">
            Loading approvals…
          </div>
        )}
        {isError && (
          <div className="rounded-xl border border-danger/30 bg-surface p-10 text-center text-sm text-danger">
            Failed to load approvals.
          </div>
        )}
        {!isLoading && items.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-surface p-12 text-center">
            <div className="text-2xl mb-2">✓</div>
            <div className="text-sm text-text-muted">No pending approvals. Agents are running clean.</div>
          </div>
        )}
        <AnimatePresence>
          {items.map((a, i) => (
            <ApprovalCard
              key={a.id}
              approval={a}
              focused={i === focused}
              onApprove={() => fireApprove(a)}
              onDeny={() => fireDeny(a)}
              onSnooze={() => fireSnooze(a)}
              exitDirection={exiting[a.id] ?? null}
            />
          ))}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {helpOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center"
            onClick={() => setHelpOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="max-w-md w-full rounded-xl border border-border bg-surface p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold mb-4">Keyboard shortcuts</h3>
              <dl className="space-y-2 text-sm">
                {[
                  ['J', 'Next approval'],
                  ['K', 'Previous approval'],
                  ['A', 'Approve focused'],
                  ['D', 'Deny focused'],
                  ['S', 'Snooze focused 2h'],
                  ['E', 'Expand/collapse payload'],
                  ['?', 'Show this help'],
                  ['Esc', 'Close dialogs'],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <dd className="text-text-muted">{v}</dd>
                    <dt>
                      <kbd className="font-mono text-xs bg-elevated border border-border rounded-md px-2 py-0.5">
                        {k}
                      </kbd>
                    </dt>
                  </div>
                ))}
              </dl>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

'use client';

import { useMemo, useState } from 'react';
import { useAgents, useApproveTask, useBatchTasks, useDenyTask, useTasks } from '@/hooks';
import { RiskBadge } from '@/components/atoms/RiskBadge';
import { UrgencyDots } from '@/components/atoms/UrgencyDots';
import { TaskDrawer } from '@/components/organisms/TaskDrawer';
import { cn, formatINRShort, formatTimeAgo } from '@/lib/utils';
import type { AgentTask, RiskLevel, TaskStatus } from '@/types';

const RISK_OPTIONS: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH'];
const STATUS_OPTIONS: TaskStatus[] = ['pending', 'running', 'success', 'failed', 'approval_required', 'denied'];

export default function TasksPage() {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState<RiskLevel[]>([]);
  const [statusFilter, setStatusFilter] = useState<TaskStatus[]>([]);
  const [agentFilter, setAgentFilter] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [openTask, setOpenTask] = useState<AgentTask | null>(null);

  const agents = useAgents();
  const { data, isLoading, isError } = useTasks({
    search: search || undefined,
    risk: riskFilter.length ? riskFilter : undefined,
    status: statusFilter.length ? statusFilter : undefined,
    agent_ids: agentFilter.length ? agentFilter : undefined,
  });

  const batch = useBatchTasks();
  const approve = useApproveTask();
  const deny = useDenyTask();

  const items = data?.items ?? [];
  const allSelected = items.length > 0 && items.every((t) => selectedIds.has(t.id));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <div className="text-xs text-text-muted">{data?.total ?? 0} total</div>
      </div>

      <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl border border-border bg-surface">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tasks…"
          className="flex-1 min-w-[220px] px-3 py-1.5 rounded-md bg-bg border border-border text-sm text-text"
        />
        <MultiSelect
          label="Agent"
          options={agents.data?.map((a) => ({ value: a.id, label: a.name })) ?? []}
          value={agentFilter}
          onChange={setAgentFilter}
        />
        <MultiSelect
          label="Risk"
          options={RISK_OPTIONS.map((r) => ({ value: r, label: r }))}
          value={riskFilter}
          onChange={(v) => setRiskFilter(v as RiskLevel[])}
        />
        <MultiSelect
          label="Status"
          options={STATUS_OPTIONS.map((r) => ({ value: r, label: r }))}
          value={statusFilter}
          onChange={(v) => setStatusFilter(v as TaskStatus[])}
        />
        <div className="ml-auto flex items-center gap-2">
          <button
            disabled={selectedIds.size === 0 || batch.isPending}
            onClick={() => batch.mutate({ ids: [...selectedIds], action: 'approve' })}
            className="px-3 py-1.5 text-xs rounded-md bg-success/15 text-success border border-success/20 disabled:opacity-40"
          >
            Approve selected ({selectedIds.size})
          </button>
          <button
            disabled={selectedIds.size === 0 || batch.isPending}
            onClick={() => batch.mutate({ ids: [...selectedIds], action: 'deny' })}
            className="px-3 py-1.5 text-xs rounded-md bg-danger/15 text-danger border border-danger/20 disabled:opacity-40"
          >
            Deny selected
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-elevated sticky top-0">
            <tr className="text-left text-[11px] uppercase tracking-widest text-text-muted">
              <th className="w-10 px-3 py-2">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={() => {
                    setSelectedIds(allSelected ? new Set() : new Set(items.map((t) => t.id)));
                  }}
                  className="accent-accent"
                />
              </th>
              <th className="w-20 px-3 py-2">#</th>
              <th className="w-32 px-3 py-2">Agent</th>
              <th className="px-3 py-2">Summary</th>
              <th className="w-24 px-3 py-2">Risk</th>
              <th className="w-32 px-3 py-2">Status</th>
              <th className="w-28 px-3 py-2">Revenue</th>
              <th className="w-24 px-3 py-2">Urgency</th>
              <th className="w-32 px-3 py-2">Created</th>
              <th className="w-28 px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={10} className="p-6 text-center text-text-muted">
                  Loading tasks…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={10} className="p-6 text-center text-danger">
                  Failed to load tasks.
                </td>
              </tr>
            )}
            {!isLoading && items.length === 0 && (
              <tr>
                <td colSpan={10} className="p-6 text-center text-text-muted">
                  No tasks match these filters.
                </td>
              </tr>
            )}
            {items.map((t) => {
              const sel = selectedIds.has(t.id);
              return (
                <tr
                  key={t.id}
                  onClick={() => setOpenTask(t)}
                  className="border-t border-border hover:bg-elevated/60 transition-colors cursor-pointer"
                >
                  <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={sel}
                      onChange={() => {
                        const next = new Set(selectedIds);
                        if (sel) next.delete(t.id);
                        else next.add(t.id);
                        setSelectedIds(next);
                      }}
                      className="accent-accent"
                    />
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-text-faint">#{t.id.slice(-4)}</td>
                  <td className="px-3 py-2 text-text-muted">{t.agent_name ?? t.agent_id}</td>
                  <td className="px-3 py-2 text-text">{t.summary}</td>
                  <td className="px-3 py-2">
                    <RiskBadge risk={t.risk} />
                  </td>
                  <td className="px-3 py-2">
                    <StatusPill status={t.status} />
                  </td>
                  <td className="px-3 py-2 tabular-nums text-right">
                    {formatINRShort(t.revenue_impact_inr)}
                  </td>
                  <td className="px-3 py-2">
                    <UrgencyDots urgency={t.urgency} />
                  </td>
                  <td className="px-3 py-2 text-text-faint text-xs">{formatTimeAgo(t.created_at)}</td>
                  <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    {t.status === 'approval_required' ? (
                      <div className="flex gap-1">
                        <button
                          onClick={() => approve.mutate(t.id)}
                          className="px-2 py-0.5 text-[10px] rounded-md bg-success/15 text-success border border-success/20"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => deny.mutate({ id: t.id })}
                          className="px-2 py-0.5 text-[10px] rounded-md bg-danger/15 text-danger border border-danger/20"
                        >
                          ✗
                        </button>
                      </div>
                    ) : (
                      <span className="text-text-faint text-xs">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <TaskDrawer
        task={openTask}
        open={!!openTask}
        onClose={() => setOpenTask(null)}
        onApprove={(id) => {
          approve.mutate(id);
          setOpenTask(null);
        }}
        onDeny={(id) => {
          deny.mutate({ id });
          setOpenTask(null);
        }}
      />
    </div>
  );
}

function StatusPill({ status }: { status: TaskStatus }) {
  const cfg: Record<TaskStatus, { dot: string; text: string }> = {
    pending: { dot: 'bg-text-faint', text: 'text-text-muted' },
    running: { dot: 'bg-accent animate-pulse-slow', text: 'text-accent' },
    success: { dot: 'bg-success', text: 'text-success' },
    failed: { dot: 'bg-danger', text: 'text-danger' },
    approval_required: { dot: 'bg-warn animate-pulse-slow', text: 'text-warn' },
    denied: { dot: 'bg-text-faint', text: 'text-text-faint' },
  };
  const c = cfg[status];
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium', c.text)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', c.dot)} />
      {status}
    </span>
  );
}

function MultiSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="px-2.5 py-1.5 text-xs rounded-md bg-bg border border-border text-text hover:border-accent/40"
      >
        {label}
        {value.length > 0 && <span className="ml-1 text-accent">({value.length})</span>}
      </button>
      {open && (
        <div className="absolute z-10 mt-1 w-56 rounded-lg border border-border bg-elevated shadow-lg p-1.5 max-h-60 overflow-y-auto">
          {options.map((o) => {
            const on = value.includes(o.value);
            return (
              <label
                key={o.value}
                className="flex items-center gap-2 px-2 py-1 hover:bg-surface rounded-md cursor-pointer text-xs"
              >
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() =>
                    onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])
                  }
                  className="accent-accent"
                />
                {o.label}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

'use client';

import { useState } from 'react';
import { Pin, PinOff, ArrowUpFromLine, Trash2 } from 'lucide-react';
import { useMemories } from '@/hooks';
import { api } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { cn, daysFromNow, formatTimeAgo } from '@/lib/utils';

export default function MemoryPage() {
  const { data, isLoading } = useMemories();
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const items = (data?.items ?? []).filter((m) => {
    if (pinnedOnly && !m.is_pinned) return false;
    if (search && !m.key.toLowerCase().includes(search.toLowerCase()) && !m.value_preview.toLowerCase().includes(search.toLowerCase()))
      return false;
    return true;
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['memories'] });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Memory vault</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Across all agents. Pin to prevent decay. Promote to skill library when repeated enough times.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search memories…"
            className="px-3 py-1.5 rounded-md bg-bg border border-border text-sm text-text w-56"
          />
          <label className="flex items-center gap-1.5 text-xs text-text-muted">
            <input type="checkbox" checked={pinnedOnly} onChange={(e) => setPinnedOnly(e.target.checked)} className="accent-accent" />
            Pinned only
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-elevated">
            <tr className="text-left text-[11px] uppercase tracking-widest text-text-muted">
              <th className="w-10 px-3 py-2"></th>
              <th className="w-32 px-3 py-2">Agent</th>
              <th className="w-40 px-3 py-2">Key</th>
              <th className="px-3 py-2">Value preview</th>
              <th className="w-24 px-3 py-2">Last used</th>
              <th className="w-24 px-3 py-2">Relevance</th>
              <th className="w-28 px-3 py-2">Decay</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-text-muted">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-text-muted">
                  No memories match.
                </td>
              </tr>
            )}
            {items.map((m) => {
              const days = m.is_pinned
                ? Infinity
                : Math.round(m.decay_half_life_days * Math.log2(Math.max(m.relevance_score, 0.01)) * -1);
              const daysLeft = Math.max(0, days);
              const danger = !m.is_pinned && daysLeft <= 2;
              const warn = !m.is_pinned && daysLeft <= 7 && !danger;
              return (
                <tr key={m.id} className="border-t border-border hover:bg-elevated/60 transition-colors">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected.has(m.id)}
                      onChange={() => {
                        const next = new Set(selected);
                        if (next.has(m.id)) next.delete(m.id);
                        else next.add(m.id);
                        setSelected(next);
                      }}
                      className="accent-accent"
                    />
                  </td>
                  <td className="px-3 py-2 text-text">{m.agent_name}</td>
                  <td className="px-3 py-2 font-mono text-xs text-text">{m.key}</td>
                  <td className="px-3 py-2 text-text-muted">{m.value_preview}</td>
                  <td className="px-3 py-2 text-text-faint text-xs">{formatTimeAgo(m.last_used_at)}</td>
                  <td className="px-3 py-2">
                    <div className="h-1.5 rounded-full bg-border overflow-hidden w-16">
                      <div
                        className={cn(
                          'h-full',
                          m.relevance_score > 0.7 ? 'bg-success' : m.relevance_score > 0.4 ? 'bg-warn' : 'bg-danger'
                        )}
                        style={{ width: `${m.relevance_score * 100}%` }}
                      />
                    </div>
                  </td>
                  <td className={cn('px-3 py-2 text-xs font-medium', danger ? 'text-danger' : warn ? 'text-warn' : 'text-text-muted')}>
                    {m.is_pinned ? '📌 Pinned' : `${daysLeft}d left${danger ? ' ⚠' : ''}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2">
        <ActionBtn
          disabled={selected.size === 0}
          onClick={async () => {
            await api.pinMemories([...selected]);
            invalidate();
          }}
          icon={<Pin size={12} />}
        >
          Pin selected
        </ActionBtn>
        <ActionBtn
          disabled={selected.size === 0}
          onClick={async () => {
            await api.unpinMemories([...selected]);
            invalidate();
          }}
          icon={<PinOff size={12} />}
        >
          Unpin selected
        </ActionBtn>
        <ActionBtn
          disabled={selected.size === 0}
          onClick={() => {}}
          icon={<ArrowUpFromLine size={12} />}
        >
          Promote to skill
        </ActionBtn>
        <ActionBtn
          disabled={selected.size === 0}
          onClick={async () => {
            await api.deleteMemories([...selected]);
            setSelected(new Set());
            invalidate();
          }}
          icon={<Trash2 size={12} />}
          danger
        >
          Delete
        </ActionBtn>
      </div>
    </div>
  );
}

function ActionBtn({
  onClick,
  disabled,
  children,
  icon,
  danger = false,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  icon?: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border',
        danger
          ? 'bg-danger/15 text-danger border-danger/20 hover:bg-danger/25'
          : 'bg-elevated text-text-muted border-border hover:text-text',
        'disabled:opacity-40 disabled:cursor-not-allowed'
      )}
    >
      {icon}
      {children}
    </button>
  );
}

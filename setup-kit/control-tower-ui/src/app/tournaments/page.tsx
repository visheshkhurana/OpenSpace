'use client';

import { useState } from 'react';
import { useTournaments } from '@/hooks';
import { TournamentArena } from '@/components/organisms/TournamentArena';
import { api } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import type { Tournament } from '@/types';

export default function TournamentsPage() {
  const { data, isLoading, isError } = useTournaments();
  const qc = useQueryClient();
  const [diffOpen, setDiffOpen] = useState<Tournament | null>(null);

  const running = (data ?? []).filter((t) => t.status === 'running' || t.status === 'pending' || t.status === 'scoring');
  const resolved = (data ?? []).filter((t) => t.status === 'resolved');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tournaments</h1>
        <button className="px-3 py-1.5 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover">
          + New tournament
        </button>
      </div>

      {isLoading && (
        <div className="rounded-xl border border-border bg-surface p-10 text-center text-sm text-text-muted">
          Loading tournaments…
        </div>
      )}
      {isError && (
        <div className="rounded-xl border border-danger/30 bg-surface p-6 text-sm text-danger">
          Failed to load tournaments.
        </div>
      )}

      <section>
        <h2 className="text-xs font-bold uppercase tracking-widest text-text-muted mb-2">
          Active ({running.length})
        </h2>
        {running.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface p-6 text-center text-sm text-text-muted">
            No active tournaments. Clone an agent to spin one up.
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {running.map((t) => (
              <TournamentArena key={t.id} tournament={t} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xs font-bold uppercase tracking-widest text-text-muted mb-2">
          Resolved ({resolved.length})
        </h2>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {resolved.map((t) => (
            <div
              key={t.id}
              onClick={() => setDiffOpen(t)}
              className="rounded-xl border border-border bg-surface p-4 hover:border-warn/40 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-warn">👑</span>
                <h4 className="text-sm font-semibold text-text">{t.title}</h4>
              </div>
              <p className="mt-2 text-xs text-text-muted">
                Winner: {t.contestants.find((c) => c.agent_id === t.winner_agent_id)?.agent_name} · Score{' '}
                {t.contestants.find((c) => c.agent_id === t.winner_agent_id)?.total_score}
              </p>
              <button className="mt-3 text-xs text-accent hover:underline">View diff →</button>
            </div>
          ))}
        </div>
      </section>

      {diffOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6"
          onClick={() => setDiffOpen(null)}
        >
          <div
            className="max-w-5xl w-full max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-surface p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold">{diffOpen.title}</h3>
              <button onClick={() => setDiffOpen(null)} className="text-text-muted hover:text-text">
                <X size={20} />
              </button>
            </div>
            <p className="text-sm text-text-muted mb-4">Task: {diffOpen.task_description}</p>

            <table className="w-full text-sm mb-4 border border-border rounded-md overflow-hidden">
              <thead className="bg-elevated">
                <tr>
                  <th className="px-3 py-2 text-left">Agent</th>
                  {diffOpen.judge_criteria.map((c) => (
                    <th key={c.id} className="px-3 py-2 text-left">
                      {c.label}
                    </th>
                  ))}
                  <th className="px-3 py-2 text-left">Total</th>
                </tr>
              </thead>
              <tbody>
                {diffOpen.contestants.map((c) => (
                  <tr key={c.agent_id} className="border-t border-border">
                    <td className="px-3 py-2">
                      {diffOpen.winner_agent_id === c.agent_id && '👑 '}
                      {c.agent_name}
                    </td>
                    {diffOpen.judge_criteria.map((jc) => (
                      <td key={jc.id} className="px-3 py-2 tabular-nums">
                        {c.scores[jc.id] ?? '—'}
                      </td>
                    ))}
                    <td className="px-3 py-2 tabular-nums font-semibold">{c.total_score ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {diffOpen.contestants.map((c) => (
                <div key={c.agent_id} className="rounded-lg border border-border p-3 bg-bg">
                  <div className="text-sm font-semibold text-text mb-2">
                    {diffOpen.winner_agent_id === c.agent_id && '👑 '}
                    {c.agent_name}
                  </div>
                  <pre className="text-[11px] font-mono text-text-muted whitespace-pre-wrap">
                    {c.final_output ?? '(still running)'}
                  </pre>
                </div>
              ))}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              {diffOpen.winner_agent_id && (
                <button
                  onClick={async () => {
                    await api.crownWinner(diffOpen.id, diffOpen.winner_agent_id!);
                    qc.invalidateQueries({ queryKey: ['tournaments'] });
                    setDiffOpen(null);
                  }}
                  className="px-3 py-1.5 text-sm rounded-md bg-warn/15 text-warn border border-warn/20 font-medium"
                >
                  Crown winner
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

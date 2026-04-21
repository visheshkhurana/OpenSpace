'use client';

import { motion } from 'framer-motion';
import { Crown, Swords } from 'lucide-react';
import type { Tournament } from '@/types';
import { cn } from '@/lib/utils';

export function TournamentArena({ tournament, onCrown }: { tournament: Tournament; onCrown?: (id: string, winnerId: string) => void }) {
  const resolved = tournament.status === 'resolved';
  const maxTokens = Math.max(...tournament.contestants.map((c) => c.output_tokens_so_far), 500);

  return (
    <motion.div
      layout
      className={cn(
        'rounded-xl border bg-surface p-4',
        resolved ? 'border-warn/30' : 'border-accent/30'
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {resolved ? <Crown size={16} className="text-warn" /> : <Swords size={16} className="text-accent" />}
          <h4 className="text-sm font-semibold text-text">{tournament.title}</h4>
        </div>
        <span
          className={cn(
            'text-[10px] px-1.5 py-0.5 rounded-md font-bold uppercase tracking-wide',
            resolved ? 'bg-warn/10 text-warn' : 'bg-accent-dim text-accent'
          )}
        >
          {tournament.status}
        </span>
      </div>
      <p className="text-xs text-text-muted mb-3">{tournament.task_description}</p>
      <div className="text-[11px] text-text-faint mb-3">
        Judge:{' '}
        {tournament.judge_criteria
          .map((c) => `${c.label} ×${c.weight}`)
          .join(' · ')}
      </div>

      <div className="space-y-2">
        {tournament.contestants.map((c) => {
          const winner = tournament.winner_agent_id === c.agent_id;
          const pct = Math.min(100, (c.output_tokens_so_far / maxTokens) * 100);
          return (
            <div key={c.agent_id} className={cn('flex items-center gap-3', resolved && !winner && 'opacity-50')}>
              <div className="w-20 text-xs font-medium text-text truncate">
                {winner && '👑 '}
                {c.agent_name}
              </div>
              <div className="flex-1 h-2 rounded-full bg-elevated overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.5 }}
                  className={cn('h-full', winner ? 'bg-warn' : c.status === 'failed' ? 'bg-danger' : 'bg-accent')}
                />
              </div>
              <div className="w-20 text-right text-[11px] font-mono text-text-muted tabular-nums">
                {c.output_tokens_so_far} tok
              </div>
              <div className="w-16 text-right text-xs font-semibold text-text tabular-nums">
                {c.total_score !== null ? c.total_score : c.status === 'running' ? '…' : '—'}
              </div>
            </div>
          );
        })}
      </div>

      {resolved && onCrown && tournament.winner_agent_id && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={() => onCrown(tournament.id, tournament.winner_agent_id!)}
            className="px-2.5 py-1 text-xs font-medium bg-warn/15 text-warn border border-warn/20 rounded-md hover:bg-warn/25"
          >
            Crown winner
          </button>
        </div>
      )}
    </motion.div>
  );
}

'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Settings2 } from 'lucide-react';
import type { MetaLearningSummary } from '@/types';
import { cn } from '@/lib/utils';

export function MetaLearningCard({ summary, isLoading }: { summary?: MetaLearningSummary; isLoading?: boolean }) {
  if (isLoading || !summary) {
    return (
      <div className="rounded-2xl border border-border bg-surface p-5 min-h-[140px] animate-pulse">
        <div className="h-3 w-32 rounded bg-elevated mb-4" />
        <div className="h-5 w-28 rounded bg-elevated" />
      </div>
    );
  }

  const spinning = summary.proposals_pending > 0;
  const deltaColor = summary.avg_quality_delta_pct >= 0 ? 'text-success' : 'text-danger';
  const deltaSign = summary.avg_quality_delta_pct >= 0 ? '+' : '';

  return (
    <Link href="/proposals" className="block focus:outline-none">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="rounded-2xl border border-accent/30 bg-surface p-5 min-h-[140px] hover:border-accent/50 hover:-translate-y-0.5 transition-all cursor-pointer"
      >
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11px] font-bold uppercase tracking-widest text-accent">META-LEARNING</div>
          <motion.span
            animate={spinning ? { rotate: 360 } : { rotate: 0 }}
            transition={spinning ? { duration: 4, repeat: Infinity, ease: 'linear' } : { duration: 0 }}
          >
            <Settings2 size={16} className="text-accent" />
          </motion.span>
        </div>
        <div className="text-2xl font-bold text-text tabular-nums">
          {summary.proposals_pending} <span className="text-sm font-medium text-text-muted">pending</span>
        </div>
        <div className="mt-2 text-xs text-text-muted space-y-0.5">
          <div>{summary.spawn_rules_proposed_this_week} spawn rules proposed</div>
          <div>
            Avg quality Δ{' '}
            <span className={cn('font-semibold tabular-nums', deltaColor)}>
              {deltaSign}
              {summary.avg_quality_delta_pct.toFixed(1)}%
            </span>
          </div>
        </div>
        <div className="mt-2 text-[11px] font-semibold text-accent">Review proposals →</div>
      </motion.div>
    </Link>
  );
}

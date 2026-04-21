'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface MetricTileProps {
  label: string;
  value: React.ReactNode;
  subtext?: React.ReactNode;
  progress?: { value: number; max: number };
  href?: string;
  accent?: boolean;
  isLoading?: boolean;
  error?: boolean;
  icon?: React.ReactNode;
  className?: string;
}

export function MetricTile({
  label,
  value,
  subtext,
  progress,
  href,
  accent = false,
  isLoading = false,
  error = false,
  icon,
  className,
}: MetricTileProps) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-surface p-5 min-h-[140px] animate-pulse">
        <div className="h-3 w-24 rounded bg-elevated mb-4" />
        <div className="h-9 w-32 rounded bg-elevated mb-3" />
        <div className="h-3 w-40 rounded bg-elevated" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-2xl border border-danger/40 bg-surface p-5 min-h-[140px]">
        <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted">{label}</div>
        <div className="mt-2 text-sm text-danger">⚠ Failed to load</div>
      </div>
    );
  }

  const body = (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn(
        'rounded-2xl border p-5 min-h-[140px] bg-surface transition-all duration-150',
        accent ? 'border-accent/40 hover:border-accent/60' : 'border-border hover:border-border/70',
        href && 'cursor-pointer hover:-translate-y-0.5',
        className
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted">{label}</div>
        {icon}
      </div>
      <div className="text-text">{value}</div>
      {progress && (
        <div className="mt-3">
          <div className="h-1.5 rounded-full bg-elevated overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, (progress.value / progress.max) * 100)}%` }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
              className="h-full bg-accent"
            />
          </div>
        </div>
      )}
      {subtext && <div className="mt-2 text-xs text-text-muted">{subtext}</div>}
    </motion.div>
  );

  return href ? (
    <Link href={href} className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-2xl">
      {body}
    </Link>
  ) : (
    body
  );
}

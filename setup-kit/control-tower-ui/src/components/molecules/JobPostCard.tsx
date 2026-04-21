'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Briefcase } from 'lucide-react';
import type { JobPost } from '@/types';
import { formatCountdown } from '@/lib/utils';

export function JobPostCard({ job, onForcePick }: { job: JobPost; onForcePick: (id: string, agentId: string) => void }) {
  const [countdown, setCountdown] = useState(() => formatCountdown(job.closes_at));
  const [pickOpen, setPickOpen] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setCountdown(formatCountdown(job.closes_at)), 60_000);
    return () => clearInterval(id);
  }, [job.closes_at]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-border bg-surface p-3 hover:border-accent/40 transition-colors"
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded-md bg-accent-dim flex items-center justify-center text-accent">
          <Briefcase size={12} />
        </div>
        <div className="font-semibold text-sm text-text">{job.title}</div>
      </div>

      <div className="flex flex-wrap gap-1 mb-2">
        {job.requirements.map((r) => (
          <span key={r} className="text-[10px] font-mono text-text-muted bg-elevated px-1.5 py-0.5 rounded-md">
            {r}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between text-[11px] text-text-muted mb-2">
        <div className="flex items-center gap-2">
          <div className="flex -space-x-1.5">
            {job.applications.slice(0, 5).map((a) => (
              <div
                key={a.id}
                title={`${a.agent_name}: ${a.pitch}`}
                className="w-5 h-5 rounded-full bg-accent-dim border border-surface flex items-center justify-center text-[9px] font-bold text-accent"
              >
                {a.agent_name.charAt(0)}
              </div>
            ))}
          </div>
          <span>{job.application_count} applicants</span>
        </div>
        <span>closes {countdown}</span>
      </div>

      <div className="relative">
        <button
          onClick={() => setPickOpen(!pickOpen)}
          className="w-full px-2 py-1.5 text-xs font-medium bg-accent-dim text-accent border border-accent/20 rounded-md hover:bg-accent/20"
        >
          Force Pick
        </button>
        {pickOpen && (
          <div className="absolute z-10 mt-1 w-full rounded-lg border border-border bg-elevated shadow-lg p-1.5 space-y-1">
            {job.applications.map((a) => (
              <button
                key={a.id}
                onClick={() => {
                  onForcePick(job.id, a.agent_id);
                  setPickOpen(false);
                }}
                className="w-full text-left px-2 py-1.5 hover:bg-surface rounded-md"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-text">{a.agent_name}</span>
                  <span className="text-text-muted tabular-nums">{a.skill_match_pct}%</span>
                </div>
                <div className="mt-0.5 h-1 rounded-full bg-border overflow-hidden">
                  <div
                    className="h-full bg-accent"
                    style={{ width: `${a.skill_match_pct}%` }}
                  />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

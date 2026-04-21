'use client';

import { motion } from 'framer-motion';
import type { SkillPrimitive } from '@/types';
import { cn } from '@/lib/utils';

interface Props {
  skill: SkillPrimitive;
  onEdit: (id: string) => void;
  onViewAgents: (id: string) => void;
}

export function SkillPrimitiveCard({ skill, onEdit, onViewAgents }: Props) {
  const quality = skill.avg_quality_score;
  const qualityColor = quality >= 80 ? 'text-success' : quality >= 60 ? 'text-warn' : 'text-danger';
  const qualityBg = quality >= 80 ? 'bg-success/10' : quality >= 60 ? 'bg-warn/10' : 'bg-danger/10';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-border bg-surface p-4 hover:border-border/70 transition-colors"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-sm font-semibold text-text">{skill.name}</div>
        <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded-md', qualityBg, qualityColor)}>
          ⭐ {quality}/100
        </span>
      </div>
      <div className="text-xs text-text-muted mb-2">×{skill.usage_count.toLocaleString()} used</div>
      <pre
        className="text-[11px] font-mono text-text-muted line-clamp-2 bg-bg rounded-md p-2 border border-border whitespace-pre-wrap"
        title={skill.prompt_fragment}
      >
        {skill.prompt_fragment_preview}
      </pre>
      <div className="mt-3 flex flex-wrap gap-1">
        {skill.tools.slice(0, 4).map((t) => (
          <span key={t} className="text-[10px] font-mono text-accent bg-accent-dim px-1.5 py-0.5 rounded-md">
            {t}
          </span>
        ))}
        {skill.tools.length > 4 && (
          <span className="text-[10px] text-text-muted">+{skill.tools.length - 4}</span>
        )}
      </div>
      <div className="mt-3 flex items-center justify-between text-xs">
        <span className="text-text-faint">avg ₹{skill.avg_cost_inr_per_call.toFixed(2)}/call</span>
        <div className="flex gap-1">
          <button onClick={() => onEdit(skill.id)} className="px-2 py-1 text-xs text-text-muted hover:text-text rounded-md">
            Edit
          </button>
          <button
            onClick={() => onViewAgents(skill.id)}
            className="px-2 py-1 text-xs text-accent bg-accent-dim border border-accent/20 rounded-md hover:bg-accent/20"
          >
            View agents
          </button>
        </div>
      </div>
    </motion.div>
  );
}

'use client';

import { forwardRef } from 'react';
import { motion } from 'framer-motion';
import {
  Brain,
  TrendingUp,
  Handshake,
  BarChart3,
  Sparkles,
  Swords,
  Crown,
  GitBranch,
  Layers,
  Briefcase,
  UserPlus,
  Copy,
  Users,
  UserMinus,
  Pin,
  Settings2,
  Cpu,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import type { ActivityEvent, ActivityEventType } from '@/types';
import { formatTimeAgo } from '@/lib/utils';

const AGENT_ICONS: Record<string, React.ElementType> = {
  MetaAgent: Brain,
  GrowthAgent: TrendingUp,
  SalesAgent: Handshake,
  DataAgent: BarChart3,
};

const EVENT_COLORS: Record<ActivityEventType, string> = {
  action: '#8B8FA8',
  success: '#22C55E',
  failure: '#EF4444',
  spawn: '#7C5CFF',
  kill: '#6B7280',
  approval_required: '#F59E0B',
  tournament_started: '#7C5CFF',
  tournament_won: '#F59E0B',
  agent_evolved: '#7C5CFF',
  skill_composed: '#06B6D4',
  job_posted: '#8B8FA8',
  applied: '#8B8FA8',
  hired: '#7C5CFF',
  cloned: '#8B8FA8',
  team_formed: '#22C55E',
  team_disbanded: '#EF4444',
  memory_pinned: '#F59E0B',
  mode_changed: '#8B8FA8',
  proposal_submitted: '#7C5CFF',
  proposal_approved: '#22C55E',
  proposal_denied: '#EF4444',
};

const EVENT_ICONS: Partial<Record<ActivityEventType, React.ElementType>> = {
  tournament_started: Swords,
  tournament_won: Crown,
  agent_evolved: GitBranch,
  skill_composed: Layers,
  job_posted: Briefcase,
  applied: UserPlus,
  hired: Handshake,
  cloned: Copy,
  team_formed: Users,
  team_disbanded: UserMinus,
  memory_pinned: Pin,
  mode_changed: Settings2,
  proposal_submitted: Cpu,
  proposal_approved: CheckCircle2,
  proposal_denied: XCircle,
};

function formatRevenue(inr: number): string {
  if (inr === 0) return '';
  if (inr >= 1_00_000) return `+₹${(inr / 1_00_000).toFixed(1)}L`;
  if (inr >= 1_000) return `+₹${(inr / 1_000).toFixed(0)}K`;
  return `+₹${inr}`;
}

function AgentAvatar({ name, eventType }: { name: string; eventType: ActivityEventType }) {
  const OverrideIcon = EVENT_ICONS[eventType];
  const Icon = OverrideIcon ?? AGENT_ICONS[name] ?? Sparkles;
  return (
    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent-dim border border-accent/20 flex items-center justify-center text-accent">
      <Icon size={12} />
    </div>
  );
}

export const ActivityEventRow = forwardRef<HTMLDivElement, { event: ActivityEvent }>(function ActivityEventRow(
  { event },
  ref
) {
  const dotColor = EVENT_COLORS[event.event_type];
  const revenue = formatRevenue(event.revenue_impact_inr);
  const timeAgo = formatTimeAgo(event.timestamp);

  return (
    <motion.div
      ref={ref}
      layout
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25, ease: [0, 0, 0.2, 1] }}
      className="flex items-start gap-2.5 px-3 py-2 rounded-lg hover:bg-elevated/60 transition-colors group"
    >
      <div className="flex-shrink-0 mt-1.5">
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: dotColor }} />
      </div>

      <AgentAvatar name={event.agent_name} eventType={event.event_type} />

      <div className="flex-1 min-w-0">
        <p className="text-[13px] leading-snug">
          <span className="font-medium text-text">{event.agent_name}</span>{' '}
          <span className="text-text-muted">{event.summary}</span>
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[11px] text-text-faint" suppressHydrationWarning>{timeAgo}</span>
          {revenue && (
            <span className="text-[11px] font-medium text-success bg-success/10 px-1.5 py-0.5 rounded-full">
              {revenue}
            </span>
          )}
          {event.event_type === 'failure' && (
            <span className="text-[11px] font-medium text-danger bg-danger/10 px-1.5 py-0.5 rounded-full">
              failed
            </span>
          )}
          {event.event_type === 'approval_required' && (
            <span className="text-[11px] font-medium text-warn bg-warn/10 px-1.5 py-0.5 rounded-full">
              needs approval
            </span>
          )}
          {event.event_type === 'hired' && (
            <span className="text-[11px] font-medium text-accent bg-accent-dim px-1.5 py-0.5 rounded-full">
              HIRED
            </span>
          )}
          {event.event_type === 'tournament_won' && (
            <span className="text-[11px] font-medium text-warn bg-warn/10 px-1.5 py-0.5 rounded-full">
              crown 👑
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
});

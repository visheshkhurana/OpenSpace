import { cn } from '@/lib/utils';
import type { AgentStatus } from '@/types';

const COLORS: Record<AgentStatus, { bg: string; ping?: string }> = {
  active: { bg: 'bg-success', ping: 'bg-success/60' },
  idle: { bg: 'bg-warn' },
  failed: { bg: 'bg-danger', ping: 'bg-danger/70' },
  killed: { bg: 'bg-text-faint' },
};

interface StatusDotProps {
  status: AgentStatus;
  size?: 'sm' | 'md';
  className?: string;
}

export function StatusDot({ status, size = 'sm', className }: StatusDotProps) {
  const dim = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3';
  const c = COLORS[status];
  const fast = status === 'failed';
  return (
    <span className={cn('relative inline-flex', dim, className)}>
      {c.ping && (
        <span
          className={cn(
            'absolute inline-flex h-full w-full rounded-full opacity-75',
            c.ping,
            fast ? 'animate-pulse-fast' : 'animate-pulse-slow'
          )}
        />
      )}
      <span className={cn('relative inline-flex rounded-full', dim, c.bg)} />
    </span>
  );
}

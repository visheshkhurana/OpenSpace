import { cn } from '@/lib/utils';
import type { AgentLevel } from '@/types';

const CONFIG: Record<AgentLevel, { bg: string; text: string; label: string }> = {
  0: { bg: 'bg-pink-500/15', text: 'text-pink-400', label: 'META' },
  1: { bg: 'bg-accent/20', text: 'text-accent', label: 'L1' },
  2: { bg: 'bg-accent/15', text: 'text-accent', label: 'L2' },
  3: { bg: 'bg-blue-500/15', text: 'text-blue-400', label: 'L3' },
};

export function LevelChip({ level, className }: { level: AgentLevel; className?: string }) {
  const c = CONFIG[level];
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-bold tracking-wider',
        c.bg,
        c.text,
        className
      )}
    >
      {c.label}
    </span>
  );
}

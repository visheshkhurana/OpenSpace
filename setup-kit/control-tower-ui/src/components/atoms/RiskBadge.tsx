import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RiskLevel } from '@/types';

const CONFIG: Record<RiskLevel, { bg: string; text: string; border: string; Icon: React.ElementType }> = {
  HIGH: { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/30', Icon: AlertTriangle },
  MEDIUM: { bg: 'bg-warn/10', text: 'text-warn', border: 'border-warn/30', Icon: AlertTriangle },
  LOW: { bg: 'bg-success/10', text: 'text-success', border: 'border-success/30', Icon: CheckCircle2 },
};

interface RiskBadgeProps {
  risk: RiskLevel;
  className?: string;
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  const c = CONFIG[risk];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full border tracking-wide',
        c.bg,
        c.text,
        c.border,
        className
      )}
    >
      <c.Icon size={10} />
      {risk}
    </span>
  );
}

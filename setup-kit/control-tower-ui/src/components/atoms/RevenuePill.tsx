import { cn } from '@/lib/utils';
import { formatINRShort } from '@/lib/utils';

export function RevenuePill({ inr, className }: { inr: number; className?: string }) {
  if (inr === 0) {
    return <span className={cn('text-[11px] text-text-faint tabular-nums', className)}>₹0</span>;
  }
  const positive = inr > 0;
  return (
    <span
      className={cn(
        'text-[11px] font-medium px-1.5 py-0.5 rounded-full tabular-nums',
        positive ? 'text-success bg-success/10' : 'text-danger bg-danger/10',
        className
      )}
    >
      {positive ? '+' : ''}
      {formatINRShort(Math.abs(inr))}
    </span>
  );
}

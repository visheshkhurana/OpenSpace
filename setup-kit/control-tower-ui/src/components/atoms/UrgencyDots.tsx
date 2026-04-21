import { cn } from '@/lib/utils';

export function UrgencyDots({ urgency }: { urgency: 1 | 2 | 3 | 4 | 5 }) {
  const color = urgency >= 4 ? 'bg-danger' : urgency === 3 ? 'bg-warn' : 'bg-text-faint';
  return (
    <span className="inline-flex gap-0.5" aria-label={`Urgency ${urgency} of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={cn('w-1.5 h-1.5 rounded-full', i <= urgency ? color : 'bg-border')}
        />
      ))}
    </span>
  );
}

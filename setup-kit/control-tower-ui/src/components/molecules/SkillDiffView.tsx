import { cn } from '@/lib/utils';
import type { SkillDiff } from '@/types';

export function SkillDiffView({ diff }: { diff: SkillDiff }) {
  return (
    <div className="rounded-lg border border-border bg-bg font-mono text-[12px] overflow-hidden max-h-[300px] overflow-y-auto">
      <div className="px-3 py-2 border-b border-border bg-elevated text-[11px] text-text-muted">
        {diff.skill_name} — v{diff.version_from} → v{diff.version_to}
      </div>
      <div className="p-2 space-y-0.5">
        {diff.chunks.map((c, i) => {
          const prefix = c.type === 'added' ? '+' : c.type === 'removed' ? '-' : ' ';
          return (
            <div key={i}>
              <div
                className={cn(
                  'px-2 py-0.5 border-l-2 whitespace-pre-wrap',
                  c.type === 'added' && 'bg-success/10 border-success text-success',
                  c.type === 'removed' && 'bg-danger/10 border-danger text-danger',
                  c.type === 'unchanged' && 'border-transparent text-text-muted'
                )}
              >
                <span className="mr-2 opacity-60">{prefix}</span>
                {c.text}
              </div>
              {c.annotation && (
                <div className="ml-6 text-text-faint italic text-[11px] px-2 py-0.5">
                  ↳ why: {c.annotation}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

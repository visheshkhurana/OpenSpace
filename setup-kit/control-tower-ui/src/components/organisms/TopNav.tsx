'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ModeSwitcher } from '@/components/molecules/ModeSwitcher';
import { useHealth, useMode, useSetMode } from '@/hooks';
import { cn } from '@/lib/utils';

const PRIMARY_LINKS = [
  { href: '/', label: 'Dashboard' },
  { href: '/agents', label: 'Agents' },
  { href: '/tasks', label: 'Tasks' },
  { href: '/metrics', label: 'Metrics' },
  { href: '/approvals', label: 'Approvals' },
  { href: '/proposals', label: 'Proposals' },
  { href: '/tournaments', label: 'Tournaments' },
  { href: '/skills', label: 'Skills' },
  { href: '/memory', label: 'Memory' },
  { href: '/settings', label: 'Settings' },
];

export function TopNav() {
  const pathname = usePathname();
  const { data: health } = useHealth();
  const { data: mode } = useMode();
  const setMode = useSetMode();

  const isHealthy = health?.status === 'ok';

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/90 backdrop-blur-md">
      <div className="flex items-center gap-6 px-6 h-[60px]">
        <Link href="/" className="flex items-center gap-2 text-text font-semibold tracking-tight">
          <span className="w-6 h-6 rounded-md bg-accent/90 flex items-center justify-center text-white font-bold text-xs">
            ◈
          </span>
          <span className="text-sm">CLEYA</span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {PRIMARY_LINKS.map((l) => {
            const active = pathname === l.href || (l.href !== '/' && pathname.startsWith(l.href));
            return (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  'relative px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  active ? 'text-text' : 'text-text-muted hover:text-text'
                )}
              >
                {l.label}
                {active && (
                  <span className="absolute left-3 right-3 -bottom-[17px] h-0.5 bg-accent rounded-full" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <ModeSwitcher
            currentMode={mode?.mode ?? 'REVIEW'}
            onModeChange={(m) => setMode.mutate(m)}
            isLoading={setMode.isPending}
          />
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <span
              className={cn(
                'w-2 h-2 rounded-full',
                isHealthy ? 'bg-success animate-pulse-slow' : 'bg-danger animate-pulse-fast'
              )}
            />
            {isHealthy ? 'Live' : 'Offline'}
          </div>
          <div className="w-8 h-8 rounded-full bg-accent-dim border border-accent/20 flex items-center justify-center text-accent text-xs font-bold">
            V
          </div>
        </div>
      </div>
    </header>
  );
}

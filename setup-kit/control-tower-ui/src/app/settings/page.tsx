'use client';

import { useMode, useSetMode } from '@/hooks';
import { ModeSwitcher } from '@/components/molecules/ModeSwitcher';
import { USE_MOCK } from '@/lib/constants';

export default function SettingsPage() {
  const { data: mode } = useMode();
  const setMode = useSetMode();

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Panel title="Founder mode">
        <p className="text-sm text-text-muted mb-3">
          Controls approval strictness. REVIEW is the default — high-risk actions require your nod.
        </p>
        <ModeSwitcher
          currentMode={mode?.mode ?? 'REVIEW'}
          onModeChange={(m) => setMode.mutate(m)}
          isLoading={setMode.isPending}
        />
      </Panel>

      <Panel title="Connection">
        <dl className="space-y-2 text-sm">
          <Row k="API Base" v={process.env.NEXT_PUBLIC_API_BASE || '—'} />
          <Row k="Mock mode" v={USE_MOCK ? 'ON (no backend needed)' : 'OFF (hitting API)'} />
          <Row k="Supabase URL" v={process.env.NEXT_PUBLIC_SUPABASE_URL || '—'} />
        </dl>
      </Panel>

      <Panel title="Mock data">
        <p className="text-sm text-text-muted mb-3">
          Set <code className="font-mono bg-elevated px-1 rounded">NEXT_PUBLIC_USE_MOCK=false</code> in your Render env
          once the orchestrator is live. Until then, the dashboard runs on seeded mock agents, tasks, and
          SSE events.
        </p>
        <button className="px-3 py-1.5 rounded-md bg-accent-dim text-accent border border-accent/20 text-xs">
          Seed mock data
        </button>
      </Panel>

      <Panel title="Notifications">
        <p className="text-sm text-text-muted">
          Hook Slack / email / push later. Right now approvals live only in-app.
        </p>
      </Panel>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-3">{title}</h2>
      {children}
    </section>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <dt className="text-text-faint">{k}</dt>
      <dd className="font-mono text-text text-xs">{v}</dd>
    </div>
  );
}

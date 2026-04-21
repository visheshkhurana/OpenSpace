'use client';

import { useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { useEconomics, useMetrics } from '@/hooks';
import { CostBurnChart } from '@/components/molecules/CostBurnChart';
import { cn, formatINRShort, formatUSD } from '@/lib/utils';
import type { AgentCostSnapshot } from '@/types';
import { AGENT_COLORS } from '@/lib/constants';

type Tab = 'overview' | 'leads' | 'agents' | 'economics';

export default function MetricsPage() {
  const [tab, setTab] = useState<Tab>('overview');
  const metrics = useMetrics();
  const econ = useEconomics();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Metrics</h1>
        <div className="inline-flex items-center rounded-lg bg-elevated border border-border p-0.5 gap-0.5">
          {(['overview', 'leads', 'agents', 'economics'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'px-2.5 py-1 text-xs font-medium rounded-md capitalize',
                tab === t ? 'bg-accent text-white' : 'text-text-muted hover:text-text'
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ChartCard title="MRR Trajectory">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics.data?.data_points ?? []}>
                <CartesianGrid stroke="#2A2D38" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" stroke="#8B8FA8" fontSize={10} tickLine={false} />
                <YAxis
                  stroke="#8B8FA8"
                  fontSize={10}
                  tickLine={false}
                  tickFormatter={(v) => `₹${(v / 1_00_000).toFixed(0)}L`}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E2028', border: '1px solid #2A2D38', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${formatINRShort(v)} (~${formatUSD(v)})`, 'MRR']}
                />
                <ReferenceLine y={41_50_000} stroke="#F59E0B" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="mrr_inr" stroke="#7C5CFF" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Leads / Day (30d)">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.data?.data_points ?? []}>
                <CartesianGrid stroke="#2A2D38" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" stroke="#8B8FA8" fontSize={10} tickLine={false} />
                <YAxis stroke="#8B8FA8" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E2028', border: '1px solid #2A2D38', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v} leads`, '']}
                />
                <Bar dataKey="leads_count" fill="#7C5CFF" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Conversion Rate (30d)">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics.data?.data_points ?? []}>
                <CartesianGrid stroke="#2A2D38" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" stroke="#8B8FA8" fontSize={10} tickLine={false} />
                <YAxis stroke="#8B8FA8" fontSize={10} tickLine={false} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E2028', border: '1px solid #2A2D38', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v.toFixed(1)}%`, 'Conv rate']}
                />
                <ReferenceLine y={8} stroke="#22C55E" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="conv_rate_pct" stroke="#22C55E" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Agent-Attributed Revenue (weekly)">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.data?.agent_revenue ?? []}>
                <CartesianGrid stroke="#2A2D38" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="week" stroke="#8B8FA8" fontSize={10} tickLine={false} />
                <YAxis stroke="#8B8FA8" fontSize={10} tickLine={false} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E2028', border: '1px solid #2A2D38', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number, name: string) => [formatINRShort(v), name]}
                />
                {['agt_growth_001', 'agt_sales_001', 'agt_outreach_001'].map((id) => (
                  <Bar
                    key={id}
                    dataKey={id}
                    stackId="rev"
                    fill={
                      id === 'agt_growth_001'
                        ? '#7C5CFF'
                        : id === 'agt_sales_001'
                          ? '#3B82F6'
                          : '#22C55E'
                    }
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {tab === 'leads' && (
        <ChartCard title="Leads per day">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={metrics.data?.data_points ?? []}>
              <CartesianGrid stroke="#2A2D38" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" stroke="#8B8FA8" fontSize={10} />
              <YAxis stroke="#8B8FA8" fontSize={10} />
              <Tooltip contentStyle={{ backgroundColor: '#1E2028', border: '1px solid #2A2D38' }} />
              <Bar dataKey="leads_count" fill="#7C5CFF" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      {tab === 'agents' && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <h3 className="text-sm font-semibold mb-3">Spawn / Kill timeline</h3>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {metrics.data?.spawn_kill_events?.map((e, i) => (
              <div key={i} className="flex items-center gap-3 text-xs py-1.5 border-b border-border last:border-0">
                <span
                  className={cn(
                    'w-2 h-2 rounded-full',
                    e.event_type === 'spawn' ? 'bg-success' : 'bg-danger'
                  )}
                />
                <span className="font-medium text-text w-32">{e.agent_name}</span>
                <span className="capitalize text-text-muted w-16">{e.event_type}</span>
                <span className="text-text-faint ml-auto">{new Date(e.timestamp).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'economics' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-surface p-5">
            <h3 className="text-sm font-semibold mb-3">This week</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <Stat label="Spend" value={formatINRShort(econ.data?.overview.total_spend_inr_this_week ?? 0)} />
              <Stat label="Revenue" value={formatINRShort(econ.data?.overview.total_revenue_inr_this_week ?? 0)} />
              <Stat label="Efficiency" value={`${(econ.data?.overview.overall_efficiency ?? 0).toFixed(1)}×`} />
              <Stat
                label="Budget used"
                value={`${Math.round((econ.data?.overview.budget_burn_pct ?? 0) * 100)}%`}
              />
            </div>
          </div>
          <ChartCard title="Weekly Budget Burn (by agent)">
            <CostBurnChart data={econ.data?.snapshots ?? []} budgetInr={5000} />
          </ChartCard>
          <EconomicsTable snapshots={econ.data?.snapshots ?? []} />
        </div>
      )}
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold mb-3">{title}</h3>
      <div className="h-64">{children}</div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] text-text-faint uppercase tracking-widest">{label}</div>
      <div className="mt-0.5 text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}

function EconomicsTable({ snapshots }: { snapshots: AgentCostSnapshot[] }) {
  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-elevated">
          <tr className="text-left text-[11px] uppercase tracking-widest text-text-muted">
            <th className="px-3 py-2">Agent</th>
            <th className="px-3 py-2">Cost/wk</th>
            <th className="px-3 py-2">Rev/wk</th>
            <th className="px-3 py-2">Efficiency</th>
            <th className="px-3 py-2">Tokens</th>
            <th className="px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((s) => (
            <tr key={s.agent_id} className="border-t border-border">
              <td className="px-3 py-2 text-text flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: AGENT_COLORS[s.agent_name] ?? '#7C5CFF' }} />
                {s.agent_name}
              </td>
              <td className="px-3 py-2 tabular-nums">{formatINRShort(s.cost_inr)}</td>
              <td className="px-3 py-2 tabular-nums">{formatINRShort(s.revenue_attributed_inr)}</td>
              <td className="px-3 py-2 tabular-nums">{s.efficiency}×</td>
              <td className="px-3 py-2 tabular-nums">{(s.tokens_input + s.tokens_output).toLocaleString()}</td>
              <td className="px-3 py-2">
                {s.over_budget ? (
                  <span className="text-xs text-danger">🔴 Over</span>
                ) : s.efficiency < 1 ? (
                  <span className="text-xs text-warn">⚠ No ROI</span>
                ) : (
                  <span className="text-xs text-success">✓ OK</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

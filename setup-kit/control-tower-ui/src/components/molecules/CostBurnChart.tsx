'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import type { AgentCostSnapshot } from '@/types';
import { AGENT_COLORS } from '@/lib/constants';

export function CostBurnChart({ data, budgetInr }: { data: AgentCostSnapshot[]; budgetInr: number }) {
  const byWeek: Record<string, Record<string, number>> = {};
  data.forEach((s) => {
    byWeek[s.week] ??= { week: 0 as any };
    byWeek[s.week][s.agent_name] = s.cost_inr;
  });
  const rows = Object.entries(byWeek).map(([week, vals]) => ({ week, ...vals }));
  const agentNames = Array.from(new Set(data.map((s) => s.agent_name)));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 16, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid stroke="#2A2D38" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="week" stroke="#8B8FA8" fontSize={11} tickLine={false} />
          <YAxis stroke="#8B8FA8" fontSize={11} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1E2028',
              border: '1px solid #2A2D38',
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v: number, name: string) => [`₹${v}`, name]}
          />
          {agentNames.map((n) => (
            <Bar key={n} dataKey={n} stackId="cost" fill={AGENT_COLORS[n] ?? '#7C5CFF'} />
          ))}
          <ReferenceLine y={budgetInr} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: 'budget', fill: '#F59E0B', fontSize: 10 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

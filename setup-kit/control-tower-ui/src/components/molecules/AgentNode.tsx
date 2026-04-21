'use client';

import { motion } from 'framer-motion';
import { Brain, TrendingUp, Handshake, BarChart3, Sparkles, Crown, Skull } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface AgentNodeData {
  id: string;
  name: string;
  level: 0 | 1 | 2 | 3;
  status: 'active' | 'idle' | 'failed' | 'killed';
  parent_id: string | null;
  current_task_summary: string | null;
  crown?: boolean;
  killed_at?: string | null;
  clone_count?: number;
}

interface AgentNodeProps {
  agent: AgentNodeData;
  onClick: (id: string) => void;
  x?: number;
  y?: number;
}

const ICONS: Record<string, React.ElementType> = {
  MetaAgent: Brain,
  GrowthAgent: TrendingUp,
  SalesAgent: Handshake,
  DataAgent: BarChart3,
};

const STATUS_COLORS = {
  active: { dot: '#22C55E', pulse: true, fast: false },
  idle: { dot: '#F59E0B', pulse: false, fast: false },
  failed: { dot: '#EF4444', pulse: true, fast: true },
  killed: { dot: '#6B7280', pulse: false, fast: false },
};

export function AgentNode({ agent, onClick, x = 0, y = 0 }: AgentNodeProps) {
  const Icon = ICONS[agent.name] ?? Sparkles;
  const { dot, pulse, fast } = STATUS_COLORS[agent.status];
  const levelLabel = agent.level === 0 ? 'META' : `L${agent.level}`;
  const isKilled = agent.status === 'killed';
  const recentlyKilled = agent.killed_at && Date.now() - new Date(agent.killed_at).getTime() < 86_400_000;

  return (
    <g transform={`translate(${x}, ${y})`}>
    <motion.g
      layoutId={`agent-node-${agent.id}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: isKilled ? 0.5 : 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      style={{ cursor: 'pointer' }}
      onClick={() => onClick(agent.id)}
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.97 }}
    >
      <rect
        x={-72}
        y={-32}
        width={144}
        height={64}
        rx={10}
        className={cn(
          'fill-[#13151B] stroke-[1.5]',
          agent.level === 0
            ? 'stroke-pink-500/40'
            : agent.level === 2
              ? 'stroke-violet-400/30'
              : 'stroke-blue-400/30'
        )}
      />

      <foreignObject x={-60} y={-20} width={24} height={24}>
        <div className="flex items-center justify-center w-6 h-6 text-text-muted">
          <Icon size={14} />
        </div>
      </foreignObject>

      <text x={-30} y={-7} fontSize={13} fontFamily="Inter, sans-serif" fontWeight={600} fill="#E6E8EE">
        {agent.name.replace('Agent', '')}
      </text>

      <rect x={-30} y={4} width={28} height={16} rx={4} fill="rgba(124,92,255,0.15)" />
      <text x={-16} y={16} fontSize={10} fontFamily="Inter, sans-serif" fontWeight={700} textAnchor="middle" fill="#7C5CFF">
        {levelLabel}
      </text>

      <circle cx={52} cy={-16} r={5} fill={dot} />
      {pulse && (
        <motion.circle
          cx={52}
          cy={-16}
          r={5}
          fill={dot}
          animate={{ opacity: [1, 0.2, 1], scale: [1, 1.8, 1] }}
          transition={{ duration: fast ? 0.5 : 2, repeat: Infinity, ease: 'easeInOut' }}
          style={{ transformOrigin: `52px -16px` }}
        />
      )}

      {agent.crown && (
        <motion.g
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 18 }}
        >
          <foreignObject x={-8} y={-48} width={16} height={16}>
            <div className="flex items-center justify-center text-warn">
              <Crown size={14} />
            </div>
          </foreignObject>
        </motion.g>
      )}

      {recentlyKilled && (
        <foreignObject x={58} y={-40} width={16} height={16}>
          <div className="flex items-center justify-center text-danger">
            <Skull size={12} />
          </div>
        </foreignObject>
      )}

      {agent.current_task_summary && (
        <text x={-60} y={26} fontSize={10} fontFamily="Inter, sans-serif" fill="#4A4E63">
          {agent.current_task_summary.slice(0, 28)}
          {agent.current_task_summary.length > 28 ? '…' : ''}
        </text>
      )}
    </motion.g>
    </g>
  );
}

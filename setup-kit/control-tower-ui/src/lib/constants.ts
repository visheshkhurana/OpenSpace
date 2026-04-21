export const DURATION = {
  fast: 150,
  base: 250,
  slow: 400,
  crawl: 800,
} as const;

export const EASE = {
  standard: [0.16, 1, 0.3, 1] as [number, number, number, number],
  in: [0.4, 0, 1, 1] as [number, number, number, number],
  out: [0, 0, 0.2, 1] as [number, number, number, number],
  sharp: [0.4, 0, 0.6, 1] as [number, number, number, number],
};

export const MRR_TARGET_INR = 41_50_000; // ₹41.5L = $50K MRR

export const AGENT_COLORS: Record<string, string> = {
  MetaAgent: '#EC4899',
  GrowthAgent: '#7C5CFF',
  SalesAgent: '#3B82F6',
  DataAgent: '#06B6D4',
  OutreachAgent: '#22C55E',
  ContentAgent: '#F59E0B',
};

export const RISK_CONFIG = {
  HIGH: { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/20' },
  MEDIUM: { bg: 'bg-warn/10', text: 'text-warn', border: 'border-warn/20' },
  LOW: { bg: 'bg-success/10', text: 'text-success', border: 'border-success/20' },
} as const;

export const TOKEN_PRICE_INR = 0.00082; // approx per token

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== 'false';

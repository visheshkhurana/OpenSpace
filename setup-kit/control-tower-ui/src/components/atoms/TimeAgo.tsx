'use client';

import { useEffect, useState } from 'react';
import { formatTimeAgo } from '@/lib/utils';

export function TimeAgo({ timestamp, className }: { timestamp: string; className?: string }) {
  // Render empty on first paint to avoid SSR/CSR mismatch — fill in on client
  const [label, setLabel] = useState<string>('');
  useEffect(() => {
    setLabel(formatTimeAgo(timestamp));
    const id = setInterval(() => setLabel(formatTimeAgo(timestamp)), 30_000);
    return () => clearInterval(id);
  }, [timestamp]);
  return <span className={className} suppressHydrationWarning>{label}</span>;
}

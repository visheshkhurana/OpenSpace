'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

interface RevenueCounterProps {
  inr: number;
  duration?: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'hero';
}

function formatINR(value: number, size: 'sm' | 'md' | 'lg' | 'hero'): string {
  if (size === 'hero' || size === 'lg') {
    if (value >= 1_00_00_000) return `₹${(value / 1_00_00_000).toFixed(1)}Cr`;
    if (value >= 1_00_000) return `₹${(value / 1_00_000).toFixed(1)}L`;
    if (value >= 1_000) return `₹${(value / 1_000).toFixed(1)}K`;
    return `₹${Math.round(value)}`;
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

const SIZE_CLASSES = {
  sm: 'text-sm font-semibold',
  md: 'text-xl font-bold',
  lg: 'text-2xl font-bold',
  hero: 'text-hero font-extrabold tracking-tight',
};

function easeOutQuart(t: number) {
  return 1 - Math.pow(1 - t, 4);
}

export function RevenueCounter({ inr, duration = 1200, className, size = 'hero' }: RevenueCounterProps) {
  const [display, setDisplay] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);
  const prevInr = useRef(0);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setDisplay(inr);
      return;
    }

    const startVal = prevInr.current;
    const endVal = inr;
    prevInr.current = inr;
    startRef.current = null;

    const step = (ts: number) => {
      if (startRef.current === null) startRef.current = ts;
      const elapsed = ts - startRef.current;
      const p = Math.min(elapsed / duration, 1);
      const eased = easeOutQuart(p);
      setDisplay(Math.round(startVal + (endVal - startVal) * eased));
      if (p < 1) rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [inr, duration]);

  return (
    <span
      className={cn(SIZE_CLASSES[size], 'tabular-nums text-text', className)}
      aria-live="polite"
      aria-label={`₹${inr.toLocaleString('en-IN')} Indian Rupees`}
    >
      {formatINR(display, size)}
    </span>
  );
}

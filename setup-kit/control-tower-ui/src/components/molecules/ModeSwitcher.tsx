'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { FounderMode } from '@/types';

interface ModeSwitcherProps {
  currentMode: FounderMode;
  onModeChange: (mode: FounderMode) => void;
  isLoading?: boolean;
}

const MODES: FounderMode[] = ['AUTO', 'REVIEW', 'MANUAL'];

const MODE_DESCRIPTIONS: Record<FounderMode, string> = {
  AUTO: 'All actions execute without approval.',
  REVIEW: 'High-risk actions require approval. Medium if cost > ₹1,000.',
  MANUAL: 'Every action requires approval. Use during audits.',
};

export function ModeSwitcher({ currentMode, onModeChange, isLoading = false }: ModeSwitcherProps) {
  const [pending, setPending] = useState<FounderMode | null>(null);

  return (
    <>
      <div className="inline-flex items-center rounded-lg bg-elevated border border-border p-0.5 gap-0.5">
        {MODES.map((m) => {
          const active = m === currentMode;
          return (
            <button
              key={m}
              onClick={() => {
                if (!active) setPending(m);
              }}
              disabled={isLoading}
              className={cn(
                'px-2.5 py-1 text-[11px] font-bold tracking-wider rounded-md transition-colors',
                active ? 'bg-accent text-white shadow-sm' : 'text-text-muted hover:text-text'
              )}
            >
              {m}
              {active && m === 'REVIEW' && (
                <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-warn align-middle" />
              )}
            </button>
          );
        })}
      </div>

      <AnimatePresence>
        {pending && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6"
            onClick={() => setPending(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="max-w-md w-full rounded-xl border border-border bg-surface p-6 shadow-xl"
            >
              <h3 className="text-lg font-semibold text-text">Switch to {pending} mode?</h3>
              <p className="mt-2 text-sm text-text-muted">{MODE_DESCRIPTIONS[pending]}</p>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  className="px-3 py-1.5 text-sm rounded-md border border-border text-text-muted hover:text-text"
                  onClick={() => setPending(null)}
                >
                  Cancel
                </button>
                <button
                  className="px-3 py-1.5 text-sm rounded-md bg-accent text-white font-medium hover:bg-accent-hover"
                  onClick={() => {
                    onModeChange(pending);
                    setPending(null);
                  }}
                >
                  Switch to {pending}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

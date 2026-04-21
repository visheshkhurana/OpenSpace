'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface MonoBlockProps {
  label?: string;
  code: string | Record<string, unknown> | null;
  collapsed?: boolean;
  className?: string;
}

export function MonoBlock({ label, code, collapsed = true, className }: MonoBlockProps) {
  const [open, setOpen] = useState(!collapsed);
  const str = typeof code === 'string' ? code : JSON.stringify(code, null, 2);

  return (
    <div className={cn('rounded-lg border border-border bg-bg', className)}>
      {label && (
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-1.5 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-text-muted hover:text-text"
        >
          <motion.span animate={{ rotate: open ? 0 : -90 }} transition={{ duration: 0.15 }}>
            <ChevronDown size={12} />
          </motion.span>
          {label}
        </button>
      )}
      <AnimatePresence initial={false}>
        {open && (
          <motion.pre
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <code className="block px-3 pb-3 pt-1 text-[11px] font-mono text-text-muted whitespace-pre-wrap break-words leading-relaxed max-h-[300px] overflow-auto">
              {str || '(empty)'}
            </code>
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

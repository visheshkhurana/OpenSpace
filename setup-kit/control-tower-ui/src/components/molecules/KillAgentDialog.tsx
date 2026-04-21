'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Skull } from 'lucide-react';
import type { Agent } from '@/types';

export function KillAgentDialog({
  agent,
  open,
  onConfirm,
  onCancel,
}: {
  agent: Agent | null;
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <AnimatePresence>
      {open && agent && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6"
          onClick={onCancel}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            className="max-w-md w-full rounded-xl border border-danger/40 bg-surface p-6 shadow-xl"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-danger/15 flex items-center justify-center text-danger flex-shrink-0">
                <Skull size={20} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-text">Kill {agent.name}?</h3>
                <p className="mt-1.5 text-sm text-text-muted">
                  This stops the agent immediately. Active tasks will be abandoned. You can respawn from a
                  prior version, but in-flight cost (₹{agent.cost_to_date_inr.toLocaleString('en-IN')}) is
                  already paid.
                </p>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button
                className="px-3 py-1.5 text-sm rounded-md border border-border text-text-muted hover:text-text"
                onClick={onCancel}
              >
                Cancel
              </button>
              <button
                className="px-3 py-1.5 text-sm rounded-md bg-danger text-white font-medium hover:bg-danger/90"
                onClick={onConfirm}
              >
                Kill agent
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import type { Agent } from '@/types';
import { TOKEN_PRICE_INR } from '@/lib/constants';

interface Props {
  sourceAgent: Agent | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (cfg: unknown) => void;
}

const AVAILABLE_TOOLS = ['send_email', 'crm_write', 'linkedin_post', 'web_search', 'calendar'];

export function CloneWizardSheet({ sourceAgent, open, onClose, onSubmit }: Props) {
  const [variants, setVariants] = useState(4);
  const [temperature, setTemperature] = useState(0.7);
  const [tools, setTools] = useState<string[]>(['send_email', 'crm_write', 'web_search']);
  const [icp, setIcp] = useState('Series A SaaS');
  const [autoTournament, setAutoTournament] = useState(true);
  const [task, setTask] = useState('Write best cold email for SaaS founders');

  const estTokens = (sourceAgent?.avg_tokens_per_task ?? 4000) * variants;
  const estCost = estTokens * TOKEN_PRICE_INR;

  return (
    <AnimatePresence>
      {open && sourceAgent && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="absolute right-0 top-0 bottom-0 w-full sm:w-[560px] bg-surface border-l border-border flex flex-col"
          >
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h2 className="text-lg font-semibold text-text">Clone {sourceAgent.name}</h2>
              <button onClick={onClose} className="text-text-muted hover:text-text">
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              <FieldLabel label={`How many variants? (${variants})`}>
                <input
                  type="range"
                  min={2}
                  max={10}
                  value={variants}
                  onChange={(e) => setVariants(+e.target.value)}
                  className="w-full accent-accent"
                />
              </FieldLabel>

              <FieldLabel label={`Temperature (${temperature.toFixed(2)})`}>
                <input
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={temperature}
                  onChange={(e) => setTemperature(+e.target.value)}
                  className="w-full accent-accent"
                />
              </FieldLabel>

              <FieldLabel label="Tool subset">
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {AVAILABLE_TOOLS.map((t) => {
                    const on = tools.includes(t);
                    return (
                      <label key={t} className="flex items-center gap-2 text-xs text-text-muted cursor-pointer">
                        <input
                          type="checkbox"
                          checked={on}
                          onChange={() =>
                            setTools((prev) => (on ? prev.filter((x) => x !== t) : [...prev, t]))
                          }
                          className="accent-accent"
                        />
                        <span className="font-mono">{t}</span>
                      </label>
                    );
                  })}
                </div>
              </FieldLabel>

              <FieldLabel label="ICP slice">
                <select
                  value={icp}
                  onChange={(e) => setIcp(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-bg border border-border text-sm text-text"
                >
                  <option>All leads</option>
                  <option>Series A SaaS</option>
                  <option>D2C Bootstrapped</option>
                  <option>Enterprise</option>
                </select>
              </FieldLabel>

              <FieldLabel label="Auto-enter tournament?">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={autoTournament}
                    onChange={(e) => setAutoTournament(e.target.checked)}
                    className="accent-accent"
                  />
                  <span className="text-xs text-text-muted">
                    {autoTournament ? 'yes — winner replaces source agent' : 'no — clones run independently'}
                  </span>
                </div>
              </FieldLabel>

              {autoTournament && (
                <FieldLabel label="Tournament task">
                  <textarea
                    rows={2}
                    value={task}
                    onChange={(e) => setTask(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-bg border border-border text-sm text-text"
                  />
                </FieldLabel>
              )}

              <div className="rounded-lg border border-border bg-bg p-3">
                <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1">
                  Preview
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  Will create <strong className="text-text">{variants}</strong> clones of {sourceAgent.name} at temperature{' '}
                  {temperature.toFixed(2)}, tools [{tools.join(', ')}], ICP: {icp}.{' '}
                  {autoTournament && 'Auto-enters tournament.'}
                </p>
                <div className="mt-2 text-xs text-text">
                  Estimated cost: <span className="font-semibold text-warn">~₹{estCost.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="border-t border-border p-5 flex justify-end gap-2">
              <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-md border border-border text-text-muted hover:text-text">
                Cancel
              </button>
              <button
                onClick={() =>
                  onSubmit({
                    source_agent_id: sourceAgent.id,
                    variant_count: variants,
                    temperature,
                    tool_subset: tools,
                    icp_slice: icp,
                    auto_tournament: autoTournament,
                    tournament_task_description: task,
                  })
                }
                className="px-3 py-1.5 text-sm rounded-md bg-accent text-white font-medium hover:bg-accent-hover"
              >
                Clone + Enter tournament →
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function FieldLabel({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1.5">{label}</div>
      {children}
    </div>
  );
}

'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { useSkills } from '@/hooks';

interface SpawnAgentSheetProps {
  parentId: string | null;
  parentLevel: number;
  open: boolean;
  onClose: () => void;
  onSpawn: (payload: { parent_id: string; name: string; skill_id: string; level: number; description: string }) => void;
}

export function SpawnAgentSheet({ parentId, parentLevel, open, onClose, onSpawn }: SpawnAgentSheetProps) {
  const [name, setName] = useState('');
  const [skillId, setSkillId] = useState('');
  const [description, setDescription] = useState('');
  const { data: skills } = useSkills();

  const submit = () => {
    if (!parentId || !name || !skillId) return;
    onSpawn({ parent_id: parentId, name, skill_id: skillId, level: parentLevel + 1, description });
    setName('');
    setSkillId('');
    setDescription('');
  };

  return (
    <AnimatePresence>
      {open && (
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
            className="absolute right-0 top-0 bottom-0 w-full sm:w-[520px] bg-surface border-l border-border flex flex-col"
          >
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h2 className="text-lg font-semibold text-text">Spawn child agent</h2>
              <button onClick={onClose} className="text-text-muted hover:text-text">
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              <Field label="Name">
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="OutreachAgent"
                  className="w-full px-3 py-2 rounded-md bg-bg border border-border text-sm text-text"
                />
              </Field>
              <Field label={`Level (auto: ${parentLevel + 1})`}>
                <div className="px-3 py-2 rounded-md bg-bg border border-border text-sm text-text-muted">
                  L{parentLevel + 1}
                </div>
              </Field>
              <Field label="Skill">
                <select
                  value={skillId}
                  onChange={(e) => setSkillId(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-bg border border-border text-sm text-text"
                >
                  <option value="">— select —</option>
                  {skills?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Description">
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="What this agent should focus on"
                  className="w-full px-3 py-2 rounded-md bg-bg border border-border text-sm text-text"
                />
              </Field>
            </div>

            <div className="border-t border-border p-5 flex justify-end gap-2">
              <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-md border border-border text-text-muted hover:text-text">
                Cancel
              </button>
              <button
                onClick={submit}
                disabled={!name || !skillId}
                className="px-3 py-1.5 text-sm rounded-md bg-accent text-white font-medium hover:bg-accent-hover disabled:opacity-40"
              >
                Spawn agent →
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1.5">{label}</span>
      {children}
    </label>
  );
}

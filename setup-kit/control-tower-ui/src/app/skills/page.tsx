'use client';

import { useState } from 'react';
import { useSkills } from '@/hooks';
import { SkillPrimitiveCard } from '@/components/molecules/SkillPrimitiveCard';
import { Plus } from 'lucide-react';

export default function SkillsPage() {
  const { data, isLoading, isError } = useSkills();
  const [search, setSearch] = useState('');

  const items = (data ?? []).filter(
    (s) =>
      !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Skill library</h1>
          <p className="text-xs text-text-muted mt-0.5">
            DNA of the agent workforce. Compose skills into agents.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search skills…"
            className="px-3 py-1.5 rounded-md bg-bg border border-border text-sm text-text w-56"
          />
          <button className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover">
            <Plus size={14} />
            New
          </button>
        </div>
      </div>

      {isLoading && <SkillsSkeleton />}
      {isError && (
        <div className="rounded-xl border border-danger/30 bg-surface p-6 text-sm text-danger">
          Failed to load skills.
        </div>
      )}
      {!isLoading && items.length === 0 && (
        <div className="rounded-xl border border-dashed border-border bg-surface p-12 text-center text-sm text-text-muted">
          No skills yet. Create your first skill primitive to start composing agents.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {items.map((s) => (
          <SkillPrimitiveCard key={s.id} skill={s} onEdit={() => {}} onViewAgents={() => {}} />
        ))}
      </div>
    </div>
  );
}

function SkillsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="rounded-xl border border-border bg-surface p-4 animate-pulse">
          <div className="h-4 w-32 bg-elevated rounded mb-3" />
          <div className="h-3 w-20 bg-elevated rounded mb-4" />
          <div className="h-12 bg-elevated rounded mb-3" />
          <div className="h-3 w-24 bg-elevated rounded" />
        </div>
      ))}
    </div>
  );
}

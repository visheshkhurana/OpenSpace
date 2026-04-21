'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getSupabase } from '@/lib/supabase';
import { USE_MOCK } from '@/lib/constants';

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();

  useEffect(() => {
    if (USE_MOCK) return;
    const supabase = getSupabase();
    if (!supabase) return;

    const channel = supabase
      .channel('control-tower')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'agents' }, () => {
        qc.invalidateQueries({ queryKey: ['agents'] });
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'tasks' }, () => {
        qc.invalidateQueries({ queryKey: ['tasks'] });
        qc.invalidateQueries({ queryKey: ['approvals'] });
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'memories' }, () => {
        qc.invalidateQueries({ queryKey: ['memories'] });
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'settings' }, () => {
        qc.invalidateQueries({ queryKey: ['mode'] });
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [qc]);

  return <>{children}</>;
}

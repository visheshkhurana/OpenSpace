'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { TaskFilters } from '@/types';

export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => api.getTasks(filters),
    refetchInterval: 10_000,
  });
}

export function useApproveTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.approveTask(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ['approvals'] });
      const prev = qc.getQueryData<any[]>(['approvals']);
      if (prev) qc.setQueryData(['approvals'], prev.filter((a: any) => a.task_id !== id));
      return { prev };
    },
    onError: (_e, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(['approvals'], ctx.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useDenyTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => api.denyTask(id, reason),
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: ['approvals'] });
      const prev = qc.getQueryData<any[]>(['approvals']);
      if (prev) qc.setQueryData(['approvals'], prev.filter((a: any) => a.task_id !== id));
      return { prev };
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(['approvals'], ctx.prev),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useSnoozeTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.snoozeTask(id, 120),
    onSettled: () => qc.invalidateQueries({ queryKey: ['approvals'] }),
  });
}

export function useBatchTasks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, action }: { ids: string[]; action: 'approve' | 'deny' }) =>
      api.batchTasks(ids, action),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['approvals'] });
    },
  });
}

'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => api.getAgents(),
    refetchInterval: 10_000,
  });
}

export function useAgent(id: string | null) {
  return useQuery({
    queryKey: ['agent', id],
    queryFn: () => api.getAgent(id!),
    enabled: !!id,
  });
}

export function useAgentVersions(id: string | null) {
  return useQuery({
    queryKey: ['agent-versions', id],
    queryFn: () => api.getAgentVersions(id!),
    enabled: !!id,
  });
}

export function useKillAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.killAgent(id),
    onSettled: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

export function useSpawnAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.spawnAgent,
    onSettled: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

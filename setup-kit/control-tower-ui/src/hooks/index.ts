'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { FounderMode } from '@/types';

export { useAgents, useAgent, useAgentVersions, useKillAgent, useSpawnAgent } from './useAgents';
export { useTasks, useApproveTask, useDenyTask, useSnoozeTask, useBatchTasks } from './useTasks';

export function useApprovals() {
  return useQuery({
    queryKey: ['approvals'],
    queryFn: () => api.getApprovals(),
    refetchInterval: 10_000,
  });
}

export function useMetricOverview() {
  return useQuery({
    queryKey: ['metric-overview'],
    queryFn: () => api.getMetricOverview(),
    refetchInterval: 10_000,
  });
}

export function useMetrics() {
  return useQuery({ queryKey: ['metrics'], queryFn: () => api.getMetrics() });
}

export function useEconomics() {
  return useQuery({ queryKey: ['economics'], queryFn: () => api.getEconomics() });
}

export function useSkills() {
  return useQuery({ queryKey: ['skills'], queryFn: () => api.getSkills() });
}

export function useTournaments() {
  return useQuery({
    queryKey: ['tournaments'],
    queryFn: () => api.getTournaments(),
    refetchInterval: 5_000,
  });
}

export function useTeams() {
  return useQuery({ queryKey: ['teams'], queryFn: () => api.getTeams() });
}

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.getJobs(),
    refetchInterval: 30_000,
  });
}

export function useMemories() {
  return useQuery({ queryKey: ['memories'], queryFn: () => api.getMemories() });
}

export function useProposals() {
  return useQuery({
    queryKey: ['proposals'],
    queryFn: () => api.getProposals(),
    refetchInterval: 15_000,
  });
}

export function useMetaSummary() {
  return useQuery({
    queryKey: ['meta-summary'],
    queryFn: () => api.getMetaSummary(),
    refetchInterval: 15_000,
  });
}

export function useMode() {
  return useQuery({ queryKey: ['mode'], queryFn: () => api.getMode() });
}

export function useSetMode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mode: FounderMode) => api.setMode(mode),
    onSettled: () => qc.invalidateQueries({ queryKey: ['mode'] }),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['healthz'],
    queryFn: () => api.healthz(),
    refetchInterval: 15_000,
  });
}

export function useTick() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.tick(),
    onSettled: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

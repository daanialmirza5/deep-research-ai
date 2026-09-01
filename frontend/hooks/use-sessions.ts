"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import type { MessageRead, ReportRead, SessionRead } from "@/lib/types";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

export const sessionsQueryKey = (projectId: string) =>
  ["sessions", projectId] as const;

export function useSessions(projectId: string | null) {
  return useQuery({
    queryKey: sessionsQueryKey(projectId ?? ""),
    queryFn: () =>
      apiClient.get<SessionRead[]>(`/projects/${projectId}/sessions`),
    enabled: projectId !== null,
    // No push channel for the list view itself (only a single session's own
    // WebSocket relays live updates) — poll while anything is still
    // queued/running so newly-created/in-flight sessions settle without a
    // manual refresh, same pattern as use-knowledge-base.ts's document list.
    refetchInterval: (query) => {
      const sessions = query.state.data;
      if (!sessions?.some((s) => ACTIVE_STATUSES.has(s.status))) return false;
      return 3000;
    },
  });
}

export function useCreateSession(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (query: string) =>
      apiClient.post<SessionRead>(`/projects/${projectId}/sessions`, { query }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: sessionsQueryKey(projectId) }),
  });
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["session", sessionId ?? ""],
    queryFn: () => apiClient.get<SessionRead>(`/sessions/${sessionId}`),
    enabled: sessionId !== null,
  });
}

export function useSessionReport(sessionId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["session-report", sessionId ?? ""],
    queryFn: () => apiClient.get<ReportRead>(`/sessions/${sessionId}/report`),
    enabled: sessionId !== null && enabled,
    retry: false,
  });
}

export function useSessionMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ["session-messages", sessionId ?? ""],
    queryFn: () =>
      apiClient.get<MessageRead[]>(`/sessions/${sessionId}/messages`),
    enabled: sessionId !== null,
  });
}

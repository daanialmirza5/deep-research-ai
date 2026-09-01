"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import type { DocumentRead, DocumentWithChunkCount, SearchResult } from "@/lib/types";

export const documentsQueryKey = (projectId: string) =>
  ["documents", projectId] as const;

const ACTIVE_STATUSES = new Set(["pending", "processing"]);

export function useDocuments(projectId: string | null) {
  return useQuery({
    queryKey: documentsQueryKey(projectId ?? ""),
    queryFn: () =>
      apiClient.get<DocumentWithChunkCount[]>(
        `/projects/${projectId}/documents`,
      ),
    enabled: projectId !== null,
    // Uploads/imports process asynchronously (Celery) with no push channel
    // of their own (unlike research sessions' WebSocket relay) — poll while
    // anything is still pending/processing, stop once everything settles.
    refetchInterval: (query) => {
      const documents = query.state.data;
      if (!documents?.some((doc) => ACTIVE_STATUSES.has(doc.status))) {
        return false;
      }
      return 2000;
    },
  });
}

export function useUploadDocument(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("project_id", projectId);
      formData.append("file", file);
      return apiClient.upload<DocumentRead>("/documents/upload", formData);
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: documentsQueryKey(projectId) }),
  });
}

export function useImportUrl(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (url: string) =>
      apiClient.post<DocumentRead>("/documents/import-url", {
        project_id: projectId,
        url,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: documentsQueryKey(projectId) }),
  });
}

export function useDeleteDocument(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      apiClient.delete(`/documents/${documentId}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: documentsQueryKey(projectId) }),
  });
}

export function useKnowledgeBaseSearch(projectId: string | null, query: string) {
  return useQuery({
    queryKey: ["knowledge-base-search", projectId, query],
    queryFn: () =>
      apiClient.get<SearchResult[]>(
        `/knowledge-base/search?project_id=${projectId}&q=${encodeURIComponent(query)}`,
      ),
    enabled: projectId !== null && query.trim().length > 0,
  });
}

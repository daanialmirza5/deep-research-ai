"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import type { AnalyticsOverview, AnalyticsUsage, RecentActivityItem } from "@/lib/types";

export function useAnalyticsOverview(days = 30) {
  return useQuery({
    queryKey: ["analytics", "overview", days],
    queryFn: () => apiClient.get<AnalyticsOverview>(`/analytics/overview?days=${days}`),
  });
}

export function useAnalyticsUsage(days = 30) {
  return useQuery({
    queryKey: ["analytics", "usage", days],
    queryFn: () => apiClient.get<AnalyticsUsage>(`/analytics/usage?days=${days}`),
  });
}

export function useAnalyticsActivity(limit = 20) {
  return useQuery({
    queryKey: ["analytics", "activity", limit],
    queryFn: () =>
      apiClient.get<RecentActivityItem[]>(`/analytics/activity?limit=${limit}`),
  });
}

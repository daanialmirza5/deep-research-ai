"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import {
  clearTokens,
  getRefreshToken,
  hasAccessToken,
  setTokens,
} from "@/lib/auth";
import type { TokenPair, UserRead } from "@/lib/types";

export const CURRENT_USER_QUERY_KEY = ["me"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: () => apiClient.get<UserRead>("/users/me"),
    enabled: hasAccessToken(),
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      apiClient.post<TokenPair>("/auth/login", credentials),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      await queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY });
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const login = useLogin();

  return useMutation({
    mutationFn: (data: {
      email: string;
      password: string;
      full_name: string;
    }) => apiClient.post<UserRead>("/auth/register", data),
    // Register returns the created user, not tokens (see docs/api-design.md
    // § Auth — register and login are deliberately separate endpoints).
    // Chaining straight into login here is a frontend UX choice, not
    // something the backend does on its behalf.
    onSuccess: (_user, variables) => login.mutateAsync(variables),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: async () => {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        await apiClient
          .post("/auth/logout", { refresh_token: refreshToken })
          .catch(() => {
            // Already-invalid/expired refresh token shouldn't block local logout.
          });
      }
    },
    onSettled: () => {
      clearTokens();
      queryClient.clear();
      router.push("/login");
    },
  });
}

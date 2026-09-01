"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";

import { ThemeProvider } from "@/components/theme-provider";
import { createQueryClient } from "@/lib/query-client";

export function Providers({ children }: { children: React.ReactNode }) {
  // One QueryClient per browser session, created lazily so it isn't shared
  // across requests on the server (React Query's own SSR guidance).
  const [queryClient] = React.useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}

"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { useCurrentUser } from "@/hooks/use-auth";
import { hasAccessToken } from "@/lib/auth";

/**
 * Client-side route guard: tokens live in localStorage (see lib/auth.ts),
 * which Next.js middleware can't read server-side, so protection happens
 * here instead of via middleware.ts. Tradeoff: a brief loading state instead
 * of a server-side redirect — acceptable for now, revisit if this moves to
 * a cookie-based token flow later.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, isError } = useCurrentUser();

  React.useEffect(() => {
    if (!hasAccessToken() || isError) {
      router.replace("/login");
    }
  }, [isError, router]);

  if (!hasAccessToken() || isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return <>{children}</>;
}

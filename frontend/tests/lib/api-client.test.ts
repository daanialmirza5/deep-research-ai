import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient, ApiError } from "@/lib/api-client";
import { clearTokens, getAccessToken, setTokens } from "@/lib/auth";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiClient", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearTokens();
  });

  it("attaches the access token as a Bearer header", async () => {
    setTokens("access-1", "refresh-1");
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(jsonResponse({ ok: true }));

    await apiClient.get("/users/me");

    const [, init] = fetchMock.mock.calls[0]!;
    const headers = init!.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer access-1");
  });

  it("sends a JSON body on POST", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(jsonResponse({}));

    await apiClient.post("/auth/login", {
      email: "a@b.com",
      password: "hunter2",
    });

    const [, init] = fetchMock.mock.calls[0]!;
    expect(init!.method).toBe("POST");
    expect(JSON.parse(init!.body as string)).toEqual({
      email: "a@b.com",
      password: "hunter2",
    });
  });

  it("refreshes the access token and retries once after a 401", async () => {
    setTokens("expired-access", "refresh-1");
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401)) // original request
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new-access",
          refresh_token: "new-refresh",
        }),
      ) // /auth/refresh
      .mockResolvedValueOnce(jsonResponse({ email: "a@b.com" })); // retried request

    const result = await apiClient.get<{ email: string }>("/users/me");

    expect(result).toEqual({ email: "a@b.com" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(getAccessToken()).toBe("new-access");
    // The retried request must use the newly-refreshed token, not the stale one.
    const retryHeaders = fetchMock.mock.calls[2]![1]!.headers as Record<
      string,
      string
    >;
    expect(retryHeaders.Authorization).toBe("Bearer new-access");
  });

  it("clears tokens and throws when refresh itself fails", async () => {
    setTokens("expired-access", "bad-refresh");
    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ detail: "invalid refresh token" }, 401),
      );

    await expect(apiClient.get("/users/me")).rejects.toBeInstanceOf(ApiError);
    expect(getAccessToken()).toBeNull();
  });

  it("surfaces the backend's problem+json detail message in ApiError", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Email is already registered" }, 409),
    );

    await expect(apiClient.post("/auth/register", {})).rejects.toMatchObject({
      status: 409,
      detail: "Email is already registered",
    });
  });
});

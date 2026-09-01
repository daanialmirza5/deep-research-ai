import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

const useCurrentUserMock = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useCurrentUser: () => useCurrentUserMock(),
}));

const hasAccessTokenMock = vi.fn();
vi.mock("@/lib/auth", () => ({
  hasAccessToken: () => hasAccessTokenMock(),
}));

import { AuthGuard } from "@/components/auth-guard";

describe("AuthGuard", () => {
  beforeEach(() => {
    replace.mockClear();
    useCurrentUserMock.mockReset();
    hasAccessTokenMock.mockReset();
  });

  it("redirects to /login when there is no access token", async () => {
    hasAccessTokenMock.mockReturnValue(false);
    useCurrentUserMock.mockReturnValue({ data: undefined, isLoading: false, isError: false });

    render(
      <AuthGuard>
        <div>secret dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("secret dashboard")).not.toBeInTheDocument();
  });

  it("redirects to /login when the current-user request errors (e.g. expired token)", async () => {
    hasAccessTokenMock.mockReturnValue(true);
    useCurrentUserMock.mockReturnValue({ data: undefined, isLoading: false, isError: true });

    render(
      <AuthGuard>
        <div>secret dashboard</div>
      </AuthGuard>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("shows a loading state and renders nothing sensitive while the user is loading", () => {
    hasAccessTokenMock.mockReturnValue(true);
    useCurrentUserMock.mockReturnValue({ data: undefined, isLoading: true, isError: false });

    render(
      <AuthGuard>
        <div>secret dashboard</div>
      </AuthGuard>,
    );

    expect(screen.queryByText("secret dashboard")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders children once a real user is loaded", () => {
    hasAccessTokenMock.mockReturnValue(true);
    useCurrentUserMock.mockReturnValue({
      data: { id: "1", email: "a@b.com" },
      isLoading: false,
      isError: false,
    });

    render(
      <AuthGuard>
        <div>secret dashboard</div>
      </AuthGuard>,
    );

    expect(screen.getByText("secret dashboard")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

let currentPathname = "/dashboard";
vi.mock("next/navigation", () => ({
  usePathname: () => currentPathname,
}));

import { Sidebar } from "@/components/layout/sidebar";

describe("Sidebar", () => {
  it("renders every nav destination", () => {
    currentPathname = "/dashboard";
    render(<Sidebar />);

    for (const label of [
      "Dashboard",
      "Workspace",
      "Knowledge Base",
      "Reports",
      "Analytics",
      "Settings",
    ]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("highlights the link matching the current route", () => {
    currentPathname = "/workspace";
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Workspace" })).toHaveClass(
      "bg-accent",
    );
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveClass(
      "bg-accent",
    );
  });

  it("highlights the parent link for a nested route", () => {
    currentPathname = "/settings/api-keys";
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Settings" })).toHaveClass(
      "bg-accent",
    );
  });
});

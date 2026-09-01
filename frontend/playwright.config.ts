import { defineConfig, devices } from "@playwright/test";

// Assumes the backend (with a migrated database) and `npm run dev` are
// already running — see docs/installation.md. Not wired into `make test`
// yet; full CI orchestration for e2e lands in Phase 12.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

import { expect, test } from "@playwright/test";

// Requires the real backend + a migrated database running (see
// docs/installation.md) — this hits actual /api/v1/auth/* endpoints, the
// same flow verified manually during Phase 6 development. Not gated behind
// an env var like the backend's integration tests since there's no
// meaningful "unit" fallback for a browser flow; skip locally with
// `npx playwright test --grep-invert auth-flow` if the backend isn't up.

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

test("register, dashboard, logout, and re-login all work end-to-end", async ({
  page,
}) => {
  const email = uniqueEmail();
  const password = "correct-horse-battery-staple";

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /multi-agent research/i }),
  ).toBeVisible();

  await page.getByRole("link", { name: /get started/i }).click();
  await page.waitForURL("**/register");

  await page.fill("#full_name", "E2E Tester");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button[type="submit"]');

  // Register chains into login (see hooks/use-auth.ts), landing on the
  // real protected dashboard, populated from a real GET /users/me call.
  await page.waitForURL("**/dashboard");
  await expect(page.getByText(email)).toBeVisible();

  await page.click('button[aria-label="Account menu"]');
  await page.getByText(/log out/i).click();
  await page.waitForURL("**/login");

  // The AuthGuard must block direct navigation without a token.
  await page.goto("/dashboard");
  await page.waitForURL("**/login");

  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard");
  await expect(page.getByText(email)).toBeVisible();
});

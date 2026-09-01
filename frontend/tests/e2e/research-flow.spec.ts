import { expect, test } from "@playwright/test";

// The genuine "core research flow" exit criterion for Phase 12
// (docs/milestones.md): register, submit a real query through the actual
// Workspace UI, watch the real multi-agent pipeline stream live progress
// over the real WebSocket relay, then view the real generated report on the
// Reports page — no direct API shortcuts, unlike analytics.spec.ts (which
// had to use them before this phase built the Workspace/Reports UI).
//
// Requires the full live stack: backend + migrated DB + real Redis broker +
// real Celery worker + Ollama + BGE, same posture as analytics.spec.ts. A
// real 6-agent run against a local CPU Ollama model takes several minutes.

function uniqueEmail(): string {
  return `e2e-research-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

test("submit a query in the Workspace, watch it run live, then read its report", async ({
  page,
}) => {
  test.setTimeout(10 * 60 * 1000);

  const email = uniqueEmail();
  const password = "correct-horse-battery-staple";
  const query = "What is few-shot prompting?";

  await page.goto("/register");
  await page.fill("#full_name", "Research Flow E2E Tester");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard");

  await page.getByRole("link", { name: /workspace/i }).click();
  await page.waitForURL("**/workspace");

  await expect(
    page.getByText(/create a project above to start a research session/i),
  ).toBeVisible();

  await page.getByPlaceholder("New project name").fill("Research Flow E2E Project");
  await page.getByRole("button", { name: "+ Project" }).click();

  await expect(page.getByPlaceholder("What would you like to research?")).toBeVisible({
    timeout: 30_000,
  });

  await page.getByPlaceholder("What would you like to research?").fill(query);
  await page.getByRole("button", { name: /research/i }).click();

  // Real proof the WebSocket relay is actually live, not just polling the
  // final state: at least one real agent node must complete and be flagged
  // "latest" before we ever wait for the terminal status.
  await expect(page.getByText("(latest)")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("Nothing streamed yet.")).toHaveCount(0);

  await expect(page.getByTestId("session-status")).toHaveText(/completed/i, {
    timeout: 6 * 60_000,
  });
  await expect(page.getByText(/view the full report/i)).toBeVisible();

  await page.getByRole("link", { name: /reports/i }).click();
  await page.waitForURL("**/reports");

  await page.getByRole("button", { name: query }).click();
  await expect(page.getByRole("heading", { name: query })).toBeVisible({
    timeout: 10_000,
  });
  // The rendered report body must contain real generated prose, not just the
  // title — proof content_markdown actually made it through react-markdown.
  // Exact match (quoted) because unquoted `text=Report` would also match the
  // page's own "Reports" heading as a substring.
  const reportCard = page.locator('text="Report"').locator("../..");
  const bodyText = await reportCard.innerText();
  expect(bodyText.length).toBeGreaterThan(query.length + 100);
});

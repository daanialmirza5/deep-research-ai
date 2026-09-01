import { expect, test } from "@playwright/test";

// Requires the real backend + a migrated database + a real Celery worker +
// MinIO all running (see docs/installation.md) — this drives the actual
// Phase 10 exit criterion through the browser: upload a document, watch it
// process to "Indexed" via the real pipeline, then find it via real
// pgvector search. Not gated behind an env var, same posture as
// auth-flow.spec.ts.

function uniqueEmail(): string {
  return `e2e-kb-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

test("upload a document, watch it index, then find it via search", async ({
  page,
}) => {
  const email = uniqueEmail();
  const password = "correct-horse-battery-staple";

  await page.goto("/register");
  await page.fill("#full_name", "KB E2E Tester");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard");

  await page.getByRole("link", { name: /knowledge base/i }).click();
  await page.waitForURL("**/knowledge-base");

  await expect(
    page.getByText(/create a project above to start/i),
  ).toBeVisible();

  await page.getByPlaceholder("New project name").fill("E2E KB Project");
  await page.getByRole("button", { name: "+ Project" }).click();

  // The first request touching container.embeddings in a freshly-started
  // API process pays a one-time BGE model load (HuggingFace Hub checks +
  // weight loading) before it can respond — this is exactly the "lean API
  // image" tension flagged in docs/architecture.md § 7 for Phase 13, not a
  // bug here. GET /projects/{id}/documents (fired right after project
  // creation) is often that first request, so give it real headroom instead
  // of the default 5s.
  await expect(page.getByText(/no documents yet/i)).toBeVisible({
    timeout: 30_000,
  });

  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "e2e-notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "Photosynthesis is the process plants use to convert sunlight into chemical energy.",
      ),
    });

  await expect(page.getByText("e2e-notes.txt")).toBeVisible();

  // Real Celery worker + real BGE embedding call — give it a real window to
  // finish rather than asserting instantly. Scoped to the status badge
  // (data-testid) rather than a plain text match: "indexed"/"Indexed"
  // also appears in this page's own descriptive copy.
  await expect(page.getByTestId("document-status")).toHaveText("Indexed", {
    timeout: 30_000,
  });

  await page
    .getByPlaceholder("Search this project's knowledge base…")
    .fill("plants converting sunlight into energy");

  await expect(page.getByText(/photosynthesis/i)).toBeVisible({
    timeout: 10_000,
  });

  await page.getByRole("button", { name: /delete document/i }).click();
  await expect(page.getByText(/no documents yet/i)).toBeVisible();
});

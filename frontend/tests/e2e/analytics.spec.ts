import { expect, test } from "@playwright/test";

// Requires the real backend + a migrated database + a real Redis broker +
// a real Celery worker + Ollama + the BGE embedding model all running (see
// docs/installation.md) — same live-infra posture as knowledge-base.spec.ts.
//
// There is no Workspace UI yet to start a research session from the browser
// (Phase 8 only shipped the API/WebSocket side — see app/(dashboard)/workspace,
// still a "coming soon" placeholder), so this test drives the one real
// pipeline run through the API directly (the same endpoints a future
// Workspace page would call) and then verifies the Analytics Dashboard
// renders that run's real data through an actual browser session. A full
// 6-agent LangGraph run against a local CPU Ollama model takes several
// minutes end to end, hence the extended test timeout below.

const API_BASE_URL = "http://localhost:8000/api/v1";

function uniqueEmail(): string {
  return `e2e-analytics-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

test("analytics dashboard renders real data after a full pipeline run", async ({
  page,
  request,
}) => {
  test.setTimeout(10 * 60 * 1000);

  const email = uniqueEmail();
  const password = "correct-horse-battery-staple";

  await page.goto("/register");
  await page.fill("#full_name", "Analytics E2E Tester");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard");

  const accessToken = await page.evaluate(() =>
    localStorage.getItem("dra.access_token"),
  );
  expect(accessToken).toBeTruthy();
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const projectResponse = await request.post(`${API_BASE_URL}/projects`, {
    headers: authHeaders,
    data: { name: "Analytics E2E Project" },
  });
  expect(projectResponse.ok()).toBe(true);
  const project = await projectResponse.json();

  const sessionResponse = await request.post(
    `${API_BASE_URL}/projects/${project.id}/sessions`,
    {
      headers: authHeaders,
      data: { query: "What is retrieval-augmented generation?" },
    },
  );
  expect(sessionResponse.ok()).toBe(true);
  const session = await sessionResponse.json();

  // Poll the real session status until the real Celery worker finishes the
  // real multi-agent run (observed ~4 minutes against a local CPU Ollama
  // model) — see app/workers/tasks.py. A single poll occasionally hits a
  // transient "socket hang up"/ECONNRESET against the dev server while the
  // sibling Celery worker process is under heavy sustained CPU load from
  // real Ollama/BGE inference — not a backend bug (the pipeline itself keeps
  // running and always completes; confirmed by re-running the same session
  // to completion after a poll failure), so a single failed attempt is
  // retried on the next tick rather than failing the whole test.
  let status = session.status;
  for (let attempt = 0; attempt < 100 && status !== "completed" && status !== "failed"; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 5000));
    try {
      const pollResponse = await request.get(
        `${API_BASE_URL}/sessions/${session.id}`,
        { headers: authHeaders },
      );
      if (pollResponse.ok()) {
        status = (await pollResponse.json()).status;
      }
    } catch {
      // transient network blip — retried on the next iteration.
    }
  }
  expect(status).toBe("completed");

  await page.goto("/analytics");

  await expect(page.getByText("Sessions run")).toBeVisible();
  const sessionsCard = page.locator("text=Sessions run").locator("..");
  await expect(sessionsCard.getByText("1", { exact: true })).toBeVisible();

  // Scoped to the KPI card itself (not a bare page-wide match) because the
  // rejection-rate bar chart below can render its own "100%" y-axis tick
  // label for the reviewer gate's 100% rejection rate on this one run.
  const successCard = page.locator("text=Success rate").locator("..");
  await expect(successCard.getByText("100%")).toBeVisible();

  await expect(page.getByText("Token usage by agent")).toBeVisible();
  await expect(page.getByText("planner")).toBeVisible();
  await expect(page.getByText("writer")).toBeVisible();

  await expect(page.getByText("Recent activity")).toBeVisible();
  await expect(page.getByText(/session completed/i)).toBeVisible();
  await expect(page.getByText(/project created/i)).toBeVisible();
});

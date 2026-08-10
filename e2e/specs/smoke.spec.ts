import { expect, test } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';
import { testIds } from '../helpers/testIds';
import { BidWorkspacePage } from '../pages/bid-workspace-page';
import { EvaluationWorkspacePage } from '../pages/evaluation-workspace-page';
import { LoginPage } from '../pages/login-page';

test.describe('m7 smoke @smoke', () => {
  test('backend OpenAPI is reachable', async ({ request }) => {
    const client = new ApiClient(request);
    const response = await client.send<{ openapi: string }>({
      path: '/api/v1/openapi.json',
    });
    expect(response.openapi).toBe('3.1.0');
  });

  test('ready health endpoint returns ok', async ({ request }) => {
    const client = new ApiClient(request);
    const result = await client.send<{ status: string }>({
      path: '/api/v1/health/ready',
    });
    expect(result.status).toBe('ok');
  });

  test('login and primary page navigation render without dead routes', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.login(
      process.env.E2E_ADMIN_EMAIL ?? 'admin@bid-platform.dev',
      process.env.E2E_ADMIN_PASSWORD ?? 'DemoAdmin123!',
    );
    await login.expectLoaded();

    const bids = new BidWorkspacePage(page);
    await bids.goto();
    await bids.clickCreate();

    await page.goto('/tasks/TASK-2026-002');
    await expect(page.getByTestId(testIds.bidDetail)).toBeVisible();

    const evaluations = new EvaluationWorkspacePage(page);
    await evaluations.goto();
    await evaluations.clickCreate();

    await page.goto('/evaluation/0190f4dd-0000-7000-8000-000000000601');
    await expect(page.getByTestId(testIds.evaluationDetail)).toBeVisible();

    for (const [path, selector] of [
      ['/admin/qualifications', 'qualification-library-page'],
      ['/admin/fragments', 'fragment-library-page'],
      ['/admin/users', 'user-permissions-page'],
      ['/admin/settings', 'system-settings-page'],
    ] as const) {
      await page.goto(path);
      await expect(page.getByTestId(selector)).toBeVisible();
    }
  });
});

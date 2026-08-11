import { expect, test } from '@playwright/test'
import { ApiClient } from '../helpers/api-client'
import { testIds } from '../helpers/testIds'
import { BidWorkspacePage } from '../pages/bid-workspace-page'
import { EvaluationWorkspacePage } from '../pages/evaluation-workspace-page'
import { LoginPage } from '../pages/login-page'

test.describe('m7 smoke @smoke', () => {
  test('backend OpenAPI is reachable', async ({ request }) => {
    const client = new ApiClient(request)
    const response = await client.send<{ openapi: string }>({
      path: '/api/v1/openapi.json',
    })
    expect(response.openapi).toBe('3.1.0')
  })

  test('ready health endpoint returns ok', async ({ request }) => {
    const client = new ApiClient(request)
    const result = await client.send<{ status: string }>({
      path: '/api/v1/health/ready',
    })
    expect(result.status).toBe('ok')
  })

  test('protected routes redirect anonymous users to login', async ({ page }) => {
    await page.goto('/admin/settings')
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByTestId(testIds.loginPage)).toBeVisible()
  })

  test('login and primary page navigation render without dead routes', async ({ page }, testInfo) => {
    const pageErrors: string[] = []
    const serverErrors: string[] = []
    page.on('pageerror', error => pageErrors.push(error.message))
    page.on('response', response => {
      if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`)
    })

    const login = new LoginPage(page)
    await login.goto()
    await login.login(
      process.env.E2E_ADMIN_EMAIL ?? 'admin@bid-platform.dev',
      process.env.E2E_ADMIN_PASSWORD ?? 'DemoAdmin123!',
    )
    await login.expectLoaded()

    const bids = new BidWorkspacePage(page)
    await bids.goto()
    await bids.clickCreate()

    await page.goto('/tasks/TASK-2026-002')
    await expect(page.getByTestId(testIds.bidDetail)).toBeVisible()
    await expect(page.getByTestId(testIds.bidTaskNotFound)).toHaveCount(0)

    const evaluations = new EvaluationWorkspacePage(page)
    await evaluations.goto()
    await evaluations.clickCreate()

    await page.goto('/evaluation/0190f4dd-0000-7000-8000-000000000601')
    await expect(page.getByTestId(testIds.evaluationDetail)).toBeVisible()
    await expect(page.getByText('评标任务不存在')).toHaveCount(0)

    for (const [path, selector, navigationLabel] of [
      ['/admin/qualifications', 'qualification-library-page', '资质库管理'],
      ['/admin/fragments', 'fragment-library-page', '文档片段库'],
      ['/admin/users', 'user-permissions-page', '用户与权限'],
      ['/admin/settings', 'system-settings-page', '系统设置'],
    ] as const) {
      if (testInfo.project.name === 'desktop') {
        await page.goto('/dashboard')
        await page.getByRole('button', { name: navigationLabel, exact: true }).click()
      } else {
        await page.goto(path)
      }
      await expect(page).toHaveURL(new RegExp(`${path}$`))
      await expect(page.getByTestId(selector)).toBeVisible()
      await expect(page.getByTestId('common-error-state')).toHaveCount(0)
    }

    expect(serverErrors, 'no page request should return HTTP 5xx').toEqual([])
    expect(pageErrors, 'no uncaught browser exception should occur').toEqual([])
  })
})

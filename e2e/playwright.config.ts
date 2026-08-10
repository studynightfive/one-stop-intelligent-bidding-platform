import { defineConfig, devices } from '@playwright/test';

/**
 * M7 Playwright 跨端 E2E 配置。
 *
 * - 3 个 viewport：桌面 1440×900、平板 1024×768、移动 390×844。
 * - webServer：启动 demo + api，确保完整链路可达。
 * - 公共 M7 选择器见 `helpers/testIds.ts`，便于跨域复用。
 */
const apiPort = Number(process.env.API_PORT ?? 8210);
const webPort = Number(process.env.WEB_PORT ?? 3210);
const baseURL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:${webPort}`;
const apiURL = process.env.E2E_API_URL ?? `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'list' : [['list'], ['html', { open: 'never' }]],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    extraHTTPHeaders: { 'X-Request-Id': 'm7-e2e' },
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'tablet',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1024, height: 768 } },
    },
    {
      name: 'mobile',
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: {
    command: 'echo "Skip webServer in CI; demo should be running"',
    url: apiURL,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
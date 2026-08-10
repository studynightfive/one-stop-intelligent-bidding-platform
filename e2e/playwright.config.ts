import { defineConfig, devices } from '@playwright/test';

const apiPort = Number(process.env.API_PORT ?? 8210);
const webPort = Number(process.env.WEB_PORT ?? 3210);
const baseURL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:${webPort}`;
const apiURL = process.env.E2E_API_URL ?? `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  testDir: './specs',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'list' : [['list'], ['html', { open: 'never' }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    channel: process.env.E2E_BROWSER_CHANNEL ?? 'chrome',
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
  metadata: { apiURL },
});

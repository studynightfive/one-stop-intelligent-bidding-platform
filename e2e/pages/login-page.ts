import type { Locator, Page } from '@playwright/test';
import { testIds } from '../helpers/testIds';

export class LoginPage {
  private readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto(): Promise<void> {
    await this.page.goto('/login');
    await this.page.getByTestId(testIds.loginPage).waitFor({ state: 'visible' });
  }

  async login(email: string, password: string): Promise<void> {
    await this.page.locator('input[autocomplete="username"]').fill(email);
    await this.page.locator('input[autocomplete="current-password"]').fill(password);
    await this.page.getByRole('button', { name: '登录', exact: true }).click();
  }

  async expectLoaded(): Promise<void> {
    const dashboard: Locator = this.page.getByTestId(testIds.bidDashboard);
    await dashboard.waitFor({ state: 'visible', timeout: 10_000 });
  }
}

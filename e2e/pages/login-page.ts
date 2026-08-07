import type { Locator, Page } from '@playwright/test';
import { testIds } from './testIds';

/**
 * 登录页 Page Object（M3 拥有，本 Phase 仅为 Phase 1+ smoke 准备）。
 */
export class LoginPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/login');
  }

  async login(email: string, password: string): Promise<void> {
    await this.page.fill(`[data-testid="${testIds.loginEmailInput}"]`, email);
    await this.page.fill(`[data-testid="${testIds.loginPasswordInput}"]`, password);
    await this.page.click(`[data-testid="${testIds.loginSubmitButton}"]`);
  }

  async expectLoaded(): Promise<void> {
    const shell: Locator = this.page.locator(`[data-testid="${testIds.appShell}"]`);
    await shell.waitFor({ state: 'visible', timeout: 5_000 });
  }
}
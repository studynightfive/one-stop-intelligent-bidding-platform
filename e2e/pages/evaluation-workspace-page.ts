import type { Locator, Page } from '@playwright/test';
import { testIds } from '../helpers/testIds';

export class EvaluationWorkspacePage {
  private readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto(): Promise<void> {
    await this.page.goto('/evaluation');
    await this.page.getByTestId(testIds.evaluationDashboard).waitFor({ state: 'visible' });
  }

  async clickCreate(): Promise<void> {
    await this.page.getByTestId(testIds.evaluationCreateButton).click();
    await this.page.getByTestId(testIds.evaluationCreate).waitFor({ state: 'visible' });
  }

  async expectDetailVisible(): Promise<void> {
    const detail: Locator = this.page.getByTestId(testIds.evaluationDetail);
    await detail.waitFor({ state: 'visible', timeout: 10_000 });
  }
}

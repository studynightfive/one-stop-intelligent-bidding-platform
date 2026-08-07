import type { Locator, Page } from '@playwright/test';
import { testIds } from '../helpers/testIds';

/**
 * 评标工作台 Page Object（M2 拥有，本 Phase 仅为 Phase 3+ smoke 准备）。
 */
export class EvaluationWorkspacePage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/evaluations');
  }

  async clickCreate(): Promise<void> {
    await this.page.click(`[data-testid="${testIds.evaluationCreateButton}"]`);
  }

  async expectRiskListVisible(): Promise<void> {
    const list: Locator = this.page.locator(`[data-testid="${testIds.evaluationRiskList}"]`);
    await list.first().waitFor({ state: 'visible', timeout: 5_000 });
  }
}
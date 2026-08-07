import type { Locator, Page } from '@playwright/test';
import { testIds } from '../helpers/testIds';

/**
 * 投标工作台 Page Object（M1 拥有，本 Phase 仅为 Phase 2+ smoke 准备）。
 */
export class BidWorkspacePage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto('/bids');
  }

  async clickCreate(): Promise<void> {
    await this.page.click(`[data-testid="${testIds.bidCreateButton}"]`);
  }

  async expectTitleVisible(): Promise<void> {
    const title: Locator = this.page.locator(`[data-testid="${testIds.bidDetailTitle}"]`);
    await title.first().waitFor({ state: 'visible', timeout: 5_000 });
  }
}
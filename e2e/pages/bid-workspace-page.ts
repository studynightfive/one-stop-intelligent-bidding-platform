import type { Locator, Page } from '@playwright/test'
import { testIds } from '../helpers/testIds'

export class BidWorkspacePage {
  private readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  async goto(): Promise<void> {
    await this.page.goto('/dashboard')
    await this.page.getByTestId(testIds.bidDashboard).waitFor({ state: 'visible' })
  }

  async clickCreate(): Promise<void> {
    await this.page.getByTestId(testIds.bidCreateButton).click()
    await this.page.getByTestId(testIds.bidCreate).waitFor({ state: 'visible' })
  }

  async expectDetailVisible(): Promise<void> {
    const detail: Locator = this.page.getByTestId(testIds.bidDetail)
    await detail.waitFor({ state: 'visible', timeout: 10_000 })
  }
}

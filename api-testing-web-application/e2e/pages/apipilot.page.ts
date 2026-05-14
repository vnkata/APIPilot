import { expect, type Page } from '@playwright/test'

const runPath = (runName: string) => `/runs/${encodeURIComponent(runName)}`

export class RunsPage {
  constructor(private readonly page: Page) {}

  async goto() {
    await this.page.goto('/runs')
  }

  async expectLoaded() {
    await expect(this.page.getByRole('heading', { name: 'Runs' })).toBeVisible()
    await expect(this.page.getByText('Run A')).toBeVisible()
  }

  async expectRunVisible(runName: string) {
    await expect(this.page.getByText(runName)).toBeVisible()
  }

  async openRun(runName: string) {
    await this.page.getByRole('link', { name: new RegExp(runName) }).click()
  }
}

export class OverviewPage {
  constructor(private readonly page: Page) {}

  async expectLoaded(runName = 'Run A') {
    await expect(this.page.getByRole('heading', { name: runName })).toBeVisible()
    await expect(this.page.getByText('Run overview')).toBeVisible()
    await expect(this.page.getByRole('main').getByText('Operations', { exact: true })).toBeVisible()
    await expect(this.page.getByRole('main').getByText('Artifacts', { exact: true })).toBeVisible()
  }
}

export class GraphPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/graph`)
  }

  async inspectNode() {
    await expect(this.page.getByRole('heading', { name: 'Graph and operations' })).toBeVisible()
    await this.page.getByRole('button', { exact: true, name: 'post-/items' }).first().click()
    await expect(this.page.getByText('Selected node')).toBeVisible()
    const dialog = this.page.getByRole('dialog', { name: 'Operation detail' })
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('post-/items')
  }
}

export class ConstraintsPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/constraints?q=limit`)
  }

  async expectFilteredConstraint() {
    await expect(this.page.getByRole('heading', { name: 'Constraints' })).toBeVisible()
    await expect(this.page.getByRole('gridcell', { name: 'input.limit >= 1' })).toBeVisible()
  }
}

export class ArtifactsPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/artifacts?artifactId=specification&raw=true`)
  }

  async expectRawViewer() {
    await expect(this.page.getByRole('heading', { name: 'Artifacts' })).toBeVisible()
    await expect(this.page.getByRole('heading', { name: 'specification' })).toBeVisible()
    await expect(this.page.getByLabel('artifact raw content')).toBeVisible()
  }
}

export class ReportsPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/reports`)
  }

  async expectLoaded() {
    await expect(this.page.getByRole('heading', { name: 'Reports' })).toBeVisible()
    await expect(this.page.getByRole('gridcell', { name: 'get-/items' }).first()).toBeVisible()
  }

  async expectMediumStatusFilterFlow() {
    await expect(this.page.getByRole('heading', { name: 'Reports' })).toBeVisible()
    await this.page.getByRole('textbox', { name: 'Status' }).fill('404')
    await expect(this.page.getByRole('gridcell', { name: 'get-/api/v1/holidays/{id}' }).first()).toBeVisible()
    await expect(this.page.getByRole('gridcell', { name: '404' }).first()).toBeVisible()
    await this.page.getByRole('button', { name: 'get-/api/v1/holidays/{id}' }).first().click()
    await expect(this.page.getByRole('dialog', { name: 'Operation detail' })).toBeVisible()
    await expect(this.page.getByText('GetHoliday')).toBeVisible()
  }
}

export class TestCasesPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/test-cases`)
  }

  async expectLoaded() {
    await expect(this.page.getByRole('heading', { name: 'Test cases' })).toBeVisible()
    await expect(this.page.getByText('tc-1')).toBeVisible()
    await this.page.getByRole('gridcell', { name: 'tc-1' }).click()
    await expect(this.page.getByRole('dialog', { name: 'Test case detail' })).toBeVisible()
  }
}

export class HistoryPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/history`)
  }

  async expectLoaded() {
    await expect(this.page.getByRole('heading', { name: 'HAR sessions' })).toBeVisible()
    await expect(this.page.getByRole('main').getByText('HTTP history')).toBeVisible()
    await expect(this.page.getByText('session-1').first()).toBeVisible()
    await expect(this.page.getByText('<REDACTED>').first()).toBeVisible()
    await this.page.getByRole('button', { name: /^session-1:/ }).first().click()
    await expect(this.page.getByRole('dialog', { name: 'HAR entry detail' })).toBeVisible()
  }
}

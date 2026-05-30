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
    await expect(this.page.getByRole('heading', { name: 'QA Mission Control' })).toBeVisible()
    await expect(this.page.getByText(runName).first()).toBeVisible()
    await expect(this.page.getByText('Run overview')).toBeVisible()
    await expect(this.page.getByRole('main').getByText('Operations', { exact: true })).toBeVisible()
    await expect(this.page.getByRole('link', { name: 'Artifact workbench' })).toBeVisible()
  }

  async expectCommandMode() {
    await expect(this.page.getByRole('heading', { name: 'QA Mission Control' })).toBeVisible()
    await expect(this.page.getByRole('link', { name: 'Review risky operations' })).toBeVisible()
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
    await expect(this.page.getByText('Navigator inspector')).toBeVisible()
    const inspector = this.page.locator('[aria-label="Operation detail"]')
    await expect(inspector).toBeVisible()
    await expect(inspector).toContainText('post-/items')
  }

  async expectJourneyMode(runName: string) {
    await this.page.goto(`${runPath(runName)}/graph?graphView=journey&graphTab=sequences`)
    await expect(this.page).toHaveURL(/graphView=journey/)
    await expect(this.page.getByRole('heading', { name: 'Dependency journey' })).toBeVisible()
    await expect(this.page.getByText(/Edges:/)).toBeVisible()
    await expect(this.page.getByText(/post-\/items -> get-\/items/)).toBeVisible()
  }

  async expectSpatialMode(runName: string) {
    await this.page.goto(`${runPath(runName)}/graph?graphView=spatial&selectedPath=seq-create-list`)
    await expect(this.page).toHaveURL(/graphView=spatial/)
    await expect(this.page.getByRole('heading', { name: 'Spatial dependency graph' })).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Spatial graph viewport' })).toBeVisible()
  }
}

export class OperationsPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/operations`)
  }

  async expectTriageFlow() {
    await expect(this.page.getByRole('heading', { name: 'Operations Explorer' })).toBeVisible()
    await expect(this.page.getByRole('grid', { name: 'operation explorer entries' })).toBeVisible()
    await this.page.getByRole('button', { name: 'get-/items' }).first().click()
    await expect(this.page.locator('[aria-label="Operation explorer detail"]')).toBeVisible()
    await expect(this.page.getByRole('link', { name: 'Graph' })).toBeVisible()
    await expect(this.page.getByRole('link', { name: 'Constraints' })).toBeVisible()
  }

  async expectCanvasMode(runName: string) {
    await this.page.goto(`${runPath(runName)}/operations?operationsView=canvas`)
    await expect(this.page).toHaveURL(/operationsView=canvas/)
    await expect(this.page.getByRole('heading', { name: 'Operation Mission Board' })).toBeVisible()
    await expect(this.page.getByRole('button', { name: 'ListItems' })).toBeVisible()
  }
}

export class ConstraintsPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/constraints?q=limit`)
  }

  async expectFilteredConstraint() {
    await expect(this.page.getByRole('heading', { name: /Constraints and invariants/ })).toBeVisible()
    await expect(this.page.getByRole('heading', { name: 'Constraint Workbench' })).toBeVisible()
    await expect(this.page.getByRole('button', { name: 'Workbench' })).toHaveAttribute('aria-pressed', 'true')
    await expect(this.page.getByText(/input\.limit/).first()).toBeVisible()
    await expect(this.page.getByRole('button', { name: 'Open detail' }).first()).toBeVisible()

    await this.page.getByRole('button', { exact: true, name: 'Explorer' }).click()
    await expect(this.page).toHaveURL(/constraintsView=table/)
    await expect(this.page).toHaveURL(/constraintTab=explorer/)
    await expect(this.page.getByRole('grid', { name: 'constraint explorer entries' })).toBeVisible()
    await expect(this.page.getByText(/input\.limit/).first()).toBeVisible()

    await this.page.getByRole('button', { exact: true, name: 'Static' }).click()
    await expect(this.page).toHaveURL(/constraintTab=static/)
    await expect(this.page.getByRole('grid', { name: 'static constraint entries' })).toBeVisible()

    await this.page.getByRole('button', { exact: true, name: 'Dynamic' }).click()
    await expect(this.page).toHaveURL(/constraintTab=dynamic/)
    await expect(this.page.getByRole('button', { exact: true, name: 'Dynamic' })).toHaveAttribute('aria-pressed', 'true')

    await this.page.getByRole('button', { exact: true, name: 'Invariants' }).click()
    await expect(this.page).toHaveURL(/constraintTab=invariants/)
    await expect(this.page.getByRole('button', { exact: true, name: 'Invariants' })).toHaveAttribute('aria-pressed', 'true')
  }

  async expectMatrixMode(runName: string) {
    await this.page.goto(`${runPath(runName)}/constraints?constraintsView=matrix`)
    await expect(this.page).toHaveURL(/constraintsView=matrix/)
    await expect(this.page.getByRole('heading', { name: 'Readiness matrix' })).toBeVisible()
    await expect(this.page.getByText(/both_present/).first()).toBeVisible()
  }
}

export class ArtifactsPage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/artifacts?artifactId=specification&artifactMode=raw`)
  }

  async expectRawViewer() {
    await expect(this.page.getByRole('heading', { name: 'Artifact Workbench' })).toBeVisible()
    await expect(this.page.getByRole('heading', { name: 'specification' })).toBeVisible()
    await expect(this.page.getByLabel('artifact raw content')).toBeVisible()
  }

  async expectWorkbenchMode(runName: string) {
    await this.page.goto(`${runPath(runName)}/artifacts?artifactsView=workbench&artifactId=specification`)
    await expect(this.page).toHaveURL(/artifactsView=workbench/)
    await expect(this.page.getByRole('heading', { name: 'Artifact Workbench' })).toBeVisible()
    await expect(this.page.getByText(/Raw policy/).first()).toBeVisible()
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
    await expect(this.page).toHaveURL(/statusCode=404/)
    const targetRow = this.page.getByRole('row', {
      name: /get-\/api\/v1\/holidays\/\{id\} 404 Client error/,
    })
    await expect(targetRow).toBeVisible()
    await targetRow.getByRole('button', { name: 'get-/api/v1/holidays/{id}' }).click()
    await expect(this.page.getByRole('dialog', { name: /operation detail/i })).toBeVisible()
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
    await expect(this.page.locator('[aria-label="Test case detail"]')).toBeVisible()
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
    await expect(this.page.locator('[aria-label="HAR entry detail"]')).toBeVisible()
  }
}

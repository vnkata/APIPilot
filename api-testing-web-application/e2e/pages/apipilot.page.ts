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
    await expect(this.page.getByRole('main').getByText(runName).first()).toBeVisible()
    await expect(this.page.getByText('Run overview')).toBeVisible()
    await expect(this.page.getByRole('main').getByText('Operations', { exact: true })).toBeVisible()
    await expect(this.page.getByRole('link', { name: 'Artifact workbench' })).toBeVisible()
  }

  async expectCommandMode() {
    await expect(this.page.getByRole('heading', { name: 'QA Mission Control' })).toBeVisible()
    await expect(this.page.getByRole('link', { name: 'Review risky operations' })).toBeVisible()
  }
}

export class WorkspacePage {
  constructor(private readonly page: Page) {}

  async goto(runName: string) {
    await this.page.goto(`${runPath(runName)}/workspace`)
  }

  async expectInvestigationWorkflow() {
    await expect(this.page.getByRole('heading', { name: 'Investigation Workspace' })).toBeVisible()
    await expect(this.page.getByRole('grid', { name: 'workspace operations' })).toBeVisible()
    await expect(this.page.getByRole('group', { name: 'Workspace layout preset' })).toBeVisible()
    await this.page.getByRole('button', { name: 'Graph focus' }).click()
    await expect
      .poll(() =>
        this.page.evaluate(() => window.localStorage.getItem('apipilot.layoutPresets.v1') ?? ''),
      )
      .toContain('"layout":"graph"')
    await this.page.getByRole('textbox', { name: 'Workspace search' }).fill('items')
    await expect(this.page).toHaveURL(/q=items/)
    await this.page.getByRole('button', { name: 'ListItems' }).first().click()
    await expect(this.page.getByText('Selected operation')).toBeVisible()
    await this.page.getByRole('button', { name: 'Inspect edge' }).first().click()
    await expect(this.page.getByText('Selected edge')).toBeVisible()
    await this.page.getByRole('button', { name: 'Bookmark selected' }).click()
    await expect(this.page.getByRole('heading', { name: 'Pinned evidence and recent activity' })).toBeVisible()
    await this.page.getByRole('button', { name: 'Save view' }).click()
    await this.page.getByRole('textbox', { name: 'View name' }).fill('Risky items')
    await this.page.getByRole('button', { exact: true, name: 'Save' }).click()
    await expect(this.page.getByRole('button', { name: 'Risky items' })).toBeVisible()
    await this.page.getByRole('button', { name: 'Risky items' }).click()
    await expect(this.page).toHaveURL(/savedViewId=/)
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
    await expect(this.page.getByRole('heading', { name: /Constraints and raw invariants/ })).toBeVisible()
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

    const rawInvariantsTab = this.page.getByRole('button', { exact: true, name: 'Raw invariants' })
    await rawInvariantsTab.focus()
    await this.page.keyboard.press('Enter')
    await expect(this.page).toHaveURL(/constraintTab=invariants/)
    await expect(rawInvariantsTab).toHaveAttribute('aria-pressed', 'true')
  }

  async expectMatrixMode(runName: string) {
    await this.page.goto(`${runPath(runName)}/constraints?constraintsView=matrix`)
    await expect(this.page).toHaveURL(/constraintsView=matrix/)
    await expect(this.page.getByRole('heading', { name: 'Readiness matrix' })).toBeVisible()
    await expect(this.page.getByText(/both_present/).first()).toBeVisible()
  }

  async completeHumanReviewWorkflow(runName: string) {
    await this.page.goto(`${runPath(runName)}/constraints?constraintsView=table&constraintTab=combination`)
    await this.page.getByRole('button', { name: 'Open guided tours' }).click()
    await this.page.getByRole('menuitem', { name: /Start Combination HITL activation/ }).click()
    await expect(this.page.getByRole('grid', { name: 'combination constraint entries' })).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Combination HITL activation' })).toContainText('1 of 7 complete')
    await this.page.getByText('Conflict needs decision').click()
    await expect(this.page.getByRole('heading', { name: 'Human review preview' })).toBeVisible()
    await this.page.getByRole('link', { name: /Open review workspace/ }).click()
    await expect(this.page.getByRole('heading', { name: 'Combination review workspace' })).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Combination HITL activation' })).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Human review workflow' })).toBeVisible()
    await expect(this.page.getByRole('img', { name: /Relation visual/ })).toHaveCount(0)
    await expect(this.page.getByRole('heading', { name: 'Run evidence readiness' })).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Runnable cases' })).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Evidence history' })).toBeVisible()
    await expect(this.page.getByText(/Runtime evidence is support, not proof/).first()).toBeVisible()
    await expect(this.page.getByRole('heading', { name: 'Final decision support' })).toBeVisible()

    await this.page.getByRole('button', { name: /^Generate draft$/ }).click()
    await expect(this.page.getByText(/The fake target returns a small item collection/)).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Combination HITL activation' })).toContainText('Generate draft: completed')

    await this.page.getByRole('button', { name: /^Approve draft$/ }).click()
    await expect(this.page.getByRole('region', { name: 'Runnable cases' })).toContainText('Approved')
    await expect(this.page.getByRole('region', { name: 'Combination HITL activation' })).toContainText('Approve case: completed')

    await this.page.getByRole('button', { name: /Use https:\/\/example\.test/ }).click()
    await expect(this.page.getByText(/HTTP method risk/)).toBeVisible()
    await this.page.getByLabel('Confirm unsafe HTTP methods for this approved run').check()
    await expect(this.page.getByRole('button', { name: /^Run approved cases$/ })).toBeEnabled()
    await this.page.getByRole('button', { name: /^Run approved cases$/ }).click()
    await expect(this.page.getByText('Run Completed').first()).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Combination HITL activation' })).toContainText('Run evidence: completed')
    const evidenceHistory = this.page.getByRole('region', { name: 'Evidence history' })
    await expect(evidenceHistory).toContainText('Executed')
    await expect(evidenceHistory).toContainText(/CONFLICT_BOTH_FALSE/)

    const acceptStatic = this.page.getByRole('button', { name: /Accept static/ })
    await acceptStatic.scrollIntoViewIfNeeded()
    await acceptStatic.click()
    await this.page.getByRole('button', { name: /^Finalize$/ }).click()
    await expect(this.page.getByText(/Human: Accept Static/).first()).toBeVisible()
    await expect(this.page.getByRole('region', { name: 'Combination HITL activation' })).toContainText('Activation complete')
    await this.page.getByRole('button', { name: /^Reopen$/ }).click()
    await expect(this.page.getByText('Reopened').first()).toBeVisible()
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

export class BuilderPage {
  constructor(private readonly page: Page) {}

  async runDryRunWriteFlow() {
    await this.page.goto('/builder/specs')
    await expect(this.page.getByRole('heading', { name: 'Spec Manager' })).toBeVisible()
    await this.page.getByRole('button', { name: 'Upload spec' }).click()
    await this.page.getByLabel('OpenAPI file').setInputFiles({
      name: 'items.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({
        openapi: '3.0.3',
        info: { title: 'Items API', version: '1.0.0' },
        servers: [{ url: 'https://example.test' }],
        paths: {
          '/items': {
            get: {
              operationId: 'listItems',
              responses: { '200': { description: 'OK' } },
            },
            post: {
              operationId: 'createItem',
              requestBody: {
                content: {
                  'application/json': {
                    schema: { type: 'object', properties: { name: { type: 'string' } } },
                  },
                },
              },
              responses: { '201': { description: 'Created' } },
            },
          },
        },
      })),
    })
    await this.page.getByRole('textbox', { name: 'Title' }).fill('Items E2E')
    await this.page.getByRole('button', { name: 'Create spec' }).click()
    await expect(this.page.getByText('items.json')).toBeVisible()
    await this.page.getByRole('link', { name: 'Preview operations' }).first().click()
    await expect(this.page.getByRole('heading', { name: 'Items E2E' })).toBeVisible()
    await expect(this.page.getByRole('grid', { name: 'spec operations' })).toBeVisible()
    await this.page.getByRole('link', { name: 'Create run config' }).click()

    await expect(this.page.getByRole('heading', { name: 'Run Config Builder' })).toBeVisible()
    await this.page.getByRole('textbox', { name: 'Config name' }).fill('Items E2E dry run')
    await this.page.getByRole('textbox', { name: 'Base URL' }).fill('https://example.test')
    await this.page.getByRole('button', { name: 'Validate config' }).click()
    await expect(this.page.getByText('Configuration is valid')).toBeVisible()
    await this.page.getByRole('button', { name: 'Create and run' }).click()
    await expect(this.page.getByRole('link', { name: 'Open execution detail' })).toBeVisible()
    await this.page.getByRole('link', { name: 'Open execution detail' }).click()

    await expect(this.page.getByRole('heading', { name: 'Execution Detail' })).toBeVisible()
    await expect(this.page.getByText(/Execution completed|completed/).first()).toBeVisible({ timeout: 10_000 })
    await expect(this.page.getByRole('link', { name: 'Open generated run' })).toBeVisible({ timeout: 10_000 })
    await this.page.getByRole('link', { name: 'Open generated run' }).click()
    await expect(this.page.getByRole('heading', { name: 'QA Mission Control' })).toBeVisible()
  }
}

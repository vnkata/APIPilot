import { expect, test } from '@playwright/test'

import {
  ArtifactsPage,
  BuilderPage,
  ConstraintsPage,
  GraphPage,
  HistoryPage,
  OperationsPage,
  OverviewPage,
  ReportsPage,
  RunsPage,
  TestCasesPage,
  WorkspacePage,
} from './pages/apipilot.page'

test('QA can inspect a sanitized APIPilot run across key artifact views', async ({ page }) => {
  const runs = new RunsPage(page)
  await runs.goto()
  await runs.expectLoaded()
  await runs.openRun('Run A')

  const overview = new OverviewPage(page)
  await overview.expectLoaded()
  await overview.expectCommandMode()

  const workspace = new WorkspacePage(page)
  await workspace.goto('Run A')
  await workspace.expectInvestigationWorkflow()

  const operations = new OperationsPage(page)
  await operations.goto('Run A')
  await operations.expectTriageFlow()
  await operations.expectCanvasMode('Run A')

  const graph = new GraphPage(page)
  await graph.goto('Run A')
  await graph.inspectNode()
  await graph.expectJourneyMode('Run A')
  await graph.expectSpatialMode('Run A')

  const constraints = new ConstraintsPage(page)
  await constraints.goto('Run A')
  await constraints.expectFilteredConstraint()
  await constraints.expectMatrixMode('Run A')

  const artifacts = new ArtifactsPage(page)
  await artifacts.goto('Run A')
  await artifacts.expectRawViewer()
  await artifacts.expectWorkbenchMode('Run A')

  const reports = new ReportsPage(page)
  await reports.goto('Run A')
  await reports.expectLoaded()

  const testCases = new TestCasesPage(page)
  await testCases.goto('Run A')
  await testCases.expectLoaded()

  const history = new HistoryPage(page)
  await history.goto('Run A')
  await history.expectLoaded()
})

test('mobile QA can inspect the medium sanitized fixture through responsive navigation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })

  const runs = new RunsPage(page)
  await runs.goto()
  await runs.expectLoaded()
  await runs.expectRunVisible('Canada Holidays Medium')
  await runs.openRun('Canada Holidays Medium')

  await new OverviewPage(page).expectLoaded('Canada Holidays Medium')

  await page.getByLabel('Open navigation').click()
  await page.getByRole('button', { name: 'Reports' }).click()

  await new ReportsPage(page).expectMediumStatusFilterFlow()
})

test('desktop QA can use command palette and compare run artifacts', async ({ page }) => {
  await page.goto('/runs/Run%20A')
  await expect(page.getByLabel('Open command palette')).toBeVisible()
  await page.keyboard.press('Control+K')
  await expect(page.getByRole('dialog', { name: 'Command palette' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Search commands' }).fill('compare')
  await page.getByRole('button', { name: /Compare runs/ }).click()
  await expect(page).toHaveURL(/\/compare/)
  await expect(page.getByRole('heading', { name: 'Compare runs' })).toBeVisible()

  await page.goto('/compare?leftRun=Run%20A&rightRun=Run%20A&artifactId=specification')
  await expect(page.getByRole('heading', { name: 'Artifact metadata diff' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'JSON structural diff' })).toBeVisible()
  await expect(page.getByText(/artifacts/).first()).toBeVisible()
  await expect(page.getByLabel('Run A artifact content').first()).toContainText('content_kind')
})

test('desktop QA can upload a spec and launch a dry-run execution', async ({ page }) => {
  await new BuilderPage(page).runDryRunWriteFlow()
})

import { test } from '@playwright/test'

import {
  ArtifactsPage,
  ConstraintsPage,
  GraphPage,
  HistoryPage,
  OperationsPage,
  OverviewPage,
  ReportsPage,
  RunsPage,
  TestCasesPage,
} from './pages/apipilot.page'

test('QA can inspect a sanitized APIPilot run across key artifact views', async ({ page }) => {
  const runs = new RunsPage(page)
  await runs.goto()
  await runs.expectLoaded()
  await runs.openRun('Run A')

  const overview = new OverviewPage(page)
  await overview.expectLoaded()
  await overview.expectCommandMode()

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

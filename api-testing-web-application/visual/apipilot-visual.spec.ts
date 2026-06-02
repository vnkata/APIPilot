import { expect, test } from '@playwright/test'

const runPath = (runName: string) => `/runs/${encodeURIComponent(runName)}`
const completedProductTourState = {
  dismissedPromptByTourId: {
    'app-shell': 2,
    artifacts: 2,
    'builder-execution-detail': 2,
    'builder-executions': 2,
    'builder-run-config': 2,
    'builder-specs': 2,
    compare: 2,
    'constraints-explorer': 2,
    'constraints-fundamentals': 2,
    'constraints-workbench': 2,
    graph: 2,
    history: 2,
    onboarding: 1,
    operations: 2,
    overview: 2,
    reports: 2,
    runs: 2,
    'test-cases': 2,
    workspace: 2,
  },
  progressByTourId: {},
  role: 'qa-qc',
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript((state) => {
    window.localStorage.setItem('apipilot.productTour.v1', JSON.stringify(state))
  }, completedProductTourState)
})

test.describe('desktop visual smoke', () => {
  test.use({ viewport: { width: 1440, height: 1000 } })

  const pages = [
    {
      name: 'runs',
      path: '/runs',
      ready: /Runs/,
    },
    {
      name: 'overview',
      path: `${runPath('Run A')}`,
      ready: /QA Mission Control/,
    },
    {
      name: 'workspace',
      path: `${runPath('Run A')}/workspace?operationKey=op-get-items`,
      ready: /Investigation Workspace/,
    },
    {
      name: 'operations',
      path: `${runPath('Run A')}/operations?operationKey=op-get-items`,
      ready: /Operations Explorer/,
    },
    {
      name: 'graph-spatial',
      path: `${runPath('Run A')}/graph?graphView=spatial&selectedPath=seq-create-list`,
      ready: /Spatial dependency graph/,
    },
    {
      name: 'artifacts',
      path: `${runPath('Run A')}/artifacts?artifactId=specification&artifactMode=summary`,
      ready: /Artifact Workbench/,
    },
    {
      name: 'compare',
      path: `/compare?leftRun=Run%20A&rightRun=Run%20A&artifactId=specification`,
      ready: /JSON structural diff/,
    },
    {
      name: 'builder-specs',
      path: '/builder/specs',
      ready: /Spec Manager/,
    },
    {
      name: 'builder-run-config',
      path: '/builder/run-configs/new?specId=spec-items',
      ready: /Run Config Builder/,
    },
    {
      name: 'builder-executions',
      path: '/builder/executions',
      ready: /Execution Center/,
    },
    {
      name: 'builder-execution-detail',
      path: '/builder/executions/exec-items',
      ready: /Execution Detail/,
    },
  ]

  for (const visualPage of pages) {
    test(`matches ${visualPage.name}`, async ({ page }) => {
      await page.goto(visualPage.path)
      await expect(page.getByRole('main')).toContainText(visualPage.ready)
      await expect(page).toHaveScreenshot(`${visualPage.name}-1440.png`, {
        animations: 'disabled',
        fullPage: true,
        maxDiffPixels: 200,
      })
    })
  }
})

test.describe('desktop 1280 visual smoke', () => {
  test.use({ viewport: { width: 1280, height: 900 } })

  for (const visualPage of [
    {
      name: 'workspace-1280',
      path: `${runPath('Run A')}/workspace?operationKey=op-get-items`,
      ready: /Investigation Workspace/,
    },
    {
      name: 'graph-spatial-1280',
      path: `${runPath('Run A')}/graph?graphView=spatial&selectedPath=seq-create-list`,
      ready: /Spatial dependency graph/,
    },
    {
      name: 'builder-run-config-1280',
      path: '/builder/run-configs/new?specId=spec-items',
      ready: /Run Config Builder/,
    },
    {
      name: 'builder-executions-1280',
      path: '/builder/executions',
      ready: /Execution Center/,
    },
    {
      name: 'compare-1280',
      path: `/compare?leftRun=Run%20A&rightRun=Run%20A&artifactId=specification`,
      ready: /JSON structural diff/,
    },
  ]) {
    test(`captures ${visualPage.name}`, async ({ page }, testInfo) => {
      await page.goto(visualPage.path)
      await expect(page.getByRole('main')).toContainText(visualPage.ready)
      await page.screenshot({
        animations: 'disabled',
        fullPage: true,
        path: testInfo.outputPath(`${visualPage.name}.png`),
      })
    })
  }
})

import { expect, test } from '@playwright/test'

const runPath = (runName: string) => `/runs/${encodeURIComponent(runName)}`

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
  ]

  for (const visualPage of pages) {
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

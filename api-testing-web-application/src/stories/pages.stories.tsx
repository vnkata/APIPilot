import { RouterProvider } from '@tanstack/react-router'
import type { Meta, StoryObj } from '@storybook/react-vite'

import { router } from '../app/router'

type RoutedPageStoryProps = {
  path: string
}

function RoutedPageStory({ path }: RoutedPageStoryProps) {
  if (typeof window !== 'undefined') {
    window.history.replaceState({}, '', path)
  }

  return <RouterProvider router={router} />
}

const meta = {
  component: RoutedPageStory,
  title: 'Pages/APIPilot',
} satisfies Meta<typeof RoutedPageStory>

export default meta

type Story = StoryObj<typeof meta>

export const Runs: Story = {
  args: { path: '/runs' },
}

export const BuilderSpecs: Story = {
  args: { path: '/builder/specs' },
}

export const BuilderSpecDetail: Story = {
  args: { path: '/builder/specs/spec-items' },
}

export const BuilderRunConfig: Story = {
  args: { path: '/builder/run-configs/new?specId=spec-items' },
}

export const BuilderExecutions: Story = {
  args: { path: '/builder/executions' },
}

export const BuilderExecutionDetail: Story = {
  args: { path: '/builder/executions/exec-items' },
}

export const Overview: Story = {
  args: { path: '/runs/Run%20A' },
}

export const Workspace: Story = {
  args: { path: '/runs/Run%20A/workspace?operationKey=op-get-items' },
}

export const Operations: Story = {
  args: { path: '/runs/Run%20A/operations?operationKey=op-get-items' },
}

export const Graph: Story = {
  args: { path: '/runs/Run%20A/graph?operationId=get-%2Fitems' },
}

export const Constraints: Story = {
  args: { path: '/runs/Run%20A/constraints?q=limit' },
}

export const Artifacts: Story = {
  args: { path: '/runs/Run%20A/artifacts?artifactId=specification&artifactMode=summary' },
}

export const Reports: Story = {
  args: { path: '/runs/Run%20A/reports' },
}

export const TestCases: Story = {
  args: { path: '/runs/Run%20A/test-cases?testCaseId=tc-1' },
}

export const History: Story = {
  args: { path: '/runs/Run%20A/history?sessionId=session-1&entryId=entry-1' },
}

export const Compare: Story = {
  args: { path: '/compare?leftRun=Run%20A&rightRun=Run%20A&artifactId=specification' },
}

export const CompareRaw: Story = {
  args: { path: '/compare?leftRun=Run%20A&rightRun=Run%20A&artifactId=specification&raw=true' },
}

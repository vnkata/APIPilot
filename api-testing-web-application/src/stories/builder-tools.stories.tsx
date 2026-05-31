import type { Meta, StoryObj } from '@storybook/react-vite'
import { http, HttpResponse } from 'msw'

import { ExecutionDetailPage } from '../features/builder/ExecutionDetailPage'
import { ExecutionsPage } from '../features/builder/ExecutionsPage'
import { RunConfigBuilderPage } from '../features/builder/RunConfigBuilderPage'
import { SpecDetailPage } from '../features/builder/SpecDetailPage'
import { SpecsPage } from '../features/builder/SpecsPage'

const meta = {
  title: 'Builder/Write Flow',
} satisfies Meta

export default meta

type Story = StoryObj

export const Specs: Story = {
  render: () => <SpecsPage />,
}

export const SpecDetail: Story = {
  render: () => <SpecDetailPage specId="spec-items" />,
}

export const RunConfigWizard: Story = {
  render: () => <RunConfigBuilderPage search={{ specId: 'spec-items' }} />,
}

export const Executions: Story = {
  render: () => <ExecutionsPage search={{}} />,
}

export const ExecutionDetail: Story = {
  render: () => <ExecutionDetailPage executionId="exec-items" />,
}

export const ValidationError: Story = {
  parameters: {
    msw: {
      handlers: [
        http.post('*/api/v1/run-configs/validate', () =>
          HttpResponse.json({ errors: ['base_url must be an absolute HTTP(S) URL'], valid: false }),
        ),
      ],
    },
  },
  render: () => <RunConfigBuilderPage search={{ specId: 'spec-items' }} />,
}

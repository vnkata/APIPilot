import type { Meta, StoryObj } from '@storybook/react-vite'

import { ApiErrorAlert } from '../shared/ui/ApiErrorAlert'
import { EmptyState } from '../shared/ui/EmptyState'
import { PageSkeleton } from '../shared/ui/PageSkeleton'

const meta = {
  title: 'Shared/States',
} satisfies Meta

export default meta

type Story = StoryObj

export const Loading: Story = {
  render: () => <PageSkeleton />,
}

export const Empty: Story = {
  render: () => <EmptyState description="No artifacts matched the current filters." title="No results" />,
}

export const Error: Story = {
  render: () => (
    <ApiErrorAlert
      error={{
        response: {
          status: 500,
        },
        isAxiosError: true,
        message: 'Request failed',
        name: 'AxiosError',
        toJSON: () => ({}),
      }}
    />
  ),
}

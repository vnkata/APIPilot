import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithProviders } from '../../test/renderWithProviders'
import { ExecutionDetailPage } from './ExecutionDetailPage'
import { ExecutionsPage } from './ExecutionsPage'
import { RunConfigBuilderPage } from './RunConfigBuilderPage'
import { SpecDetailPage } from './SpecDetailPage'
import { SpecsPage } from './SpecsPage'

describe('Builder pages', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.history.replaceState({}, '', '/builder/specs')
  })

  it('uploads an OpenAPI spec and opens the operation preview', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SpecsPage />)

    expect(await screen.findByRole('heading', { name: /spec manager/i })).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /uploaded specs/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /upload spec/i }))
    const file = new File(['{"openapi":"3.0.3","paths":{}}'], 'items.json', {
      type: 'application/json',
    })
    await user.upload(screen.getByLabelText(/openapi file/i), file)
    await user.type(screen.getByRole('textbox', { name: /title/i }), 'Items uploaded')
    await user.click(screen.getByRole('button', { name: /create spec/i }))

    expect(await screen.findByText(/items.json/i)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /preview operations/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/builder/specs/spec-items'),
    )
  })

  it('shows spec metadata, operation preview, and config CTA', async () => {
    renderWithProviders(<SpecDetailPage specId="spec-items" />)

    expect(await screen.findByRole('heading', { name: /items api/i })).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /spec operations/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create run config/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/builder/run-configs/new?specId=spec-items'),
    )
  })

  it('validates and creates a dry-run config without persisting sensitive fields', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RunConfigBuilderPage search={{ specId: 'spec-items' }} />)

    expect(await screen.findByRole('heading', { name: /run config builder/i })).toBeInTheDocument()
    await user.clear(await screen.findByRole('textbox', { name: /config name/i }))
    await user.type(screen.getByRole('textbox', { name: /config name/i }), 'Items dry run')
    await user.type(await screen.findByRole('textbox', { name: /base url/i }), 'https://example.test')
    await user.click(screen.getByRole('button', { name: /headers/i }))
    await user.type(screen.getByRole('textbox', { name: /header name/i }), 'Authorization')
    await user.type(screen.getByRole('textbox', { name: /env variable name/i }), 'API_TOKEN')
    await user.click(screen.getByRole('button', { name: /validate config/i }))

    expect(await screen.findByText(/configuration is valid/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^create config$/i }))
    expect(await screen.findByText(/config created/i)).toBeInTheDocument()
    expect(window.localStorage.getItem('apipilot.runConfigDrafts.v1')).not.toContain('API_TOKEN')
  })

  it('guides Builder users with config summary, validation status, and empty-state CTAs', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RunConfigBuilderPage search={{ specId: 'spec-items' }} />)

    expect(await screen.findByRole('heading', { name: /run config builder/i })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /run config summary/i })).toBeInTheDocument()
    expect(screen.getByText(/mode: dry run/i)).toBeInTheDocument()
    expect(screen.getByText(/validation: not run/i)).toBeInTheDocument()
    expect(screen.getByText(/dry run uses deterministic local execution/i)).toBeInTheDocument()

    await user.type(await screen.findByRole('textbox', { name: /base url/i }), 'https://example.test')
    await user.click(screen.getByRole('button', { name: /validate config/i }))

    expect(await screen.findByText(/validation: valid/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create and run/i })).toBeInTheDocument()
  })

  it('lists executions, opens detail, and exposes generated run CTA', async () => {
    renderWithProviders(<ExecutionsPage search={{}} />)

    expect(await screen.findByRole('heading', { name: /execution center/i })).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /executions/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open detail/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/builder/executions/exec-items'),
    )
    expect(screen.getByRole('link', { name: /open generated run/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/runs/Items-API-exec-items'),
    )
  })

  it('renders execution timeline with sanitized metadata and cancel affordance', async () => {
    renderWithProviders(<ExecutionDetailPage executionId="exec-items" />)

    expect(await screen.findByRole('heading', { name: /execution detail/i })).toBeInTheDocument()
    expect(await screen.findByText(/execution completed/i)).toBeInTheDocument()
    expect(screen.getByText(/<REDACTED>/i)).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole('link', { name: /open generated run/i })).toHaveAttribute(
        'href',
        expect.stringContaining('/runs/Items-API-exec-items'),
      ),
    )
  })
})

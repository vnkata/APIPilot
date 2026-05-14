import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { graphEdges } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { GraphPage } from './GraphPage'

describe('GraphPage', () => {
  it('renders the dependency graph with search and edge table controls', async () => {
    renderWithProviders(<GraphPage runName="Run A" search={{ q: '', limit: 25, offset: 0 }} />)

    expect((await screen.findAllByText('post-/items')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('get-/items').length).toBeGreaterThan(0)
    expect(screen.getByRole('textbox', { name: /search graph/i })).toBeInTheDocument()
    expect(screen.getByRole('grid', { name: /graph edges/i })).toBeInTheDocument()
  })

  it('shows selected node details from URL-backed operationId', async () => {
    renderWithProviders(
      <GraphPage runName="Run A" search={{ operationId: 'post-/items', q: '', limit: 25, offset: 0 }} />,
    )

    expect(await screen.findByText(/selected node/i)).toBeInTheDocument()
    expect(screen.getByText(/outgoing/i)).toBeInTheDocument()
  })

  it('opens operation details from URL-backed operationId', async () => {
    renderWithProviders(
      <GraphPage runName="Run A" search={{ operationId: 'get-/items', q: '', limit: 25, offset: 0 }} />,
    )

    expect(await screen.findByRole('dialog', { name: /operation detail/i })).toBeInTheDocument()
    expect(await screen.findByText('ListItems')).toBeInTheDocument()
  })

  it('maps edge filters to the backend and opens URL-backed edge details', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/graph/edges', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(graphEdges)
      }),
    )

    renderWithProviders(
      <GraphPage
        runName="Run A"
        search={{
          edgeId: 'post-/items=>get-/items::item.id|itemId|response to parameter via test',
          fromNode: 'post-/items',
          groupBy: 'from_node',
          limit: 10,
          offset: 0,
          q: 'items',
          toNode: 'get-/items',
        }}
      />,
    )

    await waitFor(() => expect(requestedUrl?.searchParams.get('from_node')).toBe('post-/items'))
    expect(requestedUrl?.searchParams.get('to_node')).toBe('get-/items')
    expect(requestedUrl?.searchParams.get('group_by')).toBe('from_node')
    expect(requestedUrl?.searchParams.get('limit')).toBe('10')
    expect(await screen.findByRole('dialog', { name: /edge detail/i })).toBeInTheDocument()
    expect(screen.getByText('item.id')).toBeInTheDocument()
  })
})

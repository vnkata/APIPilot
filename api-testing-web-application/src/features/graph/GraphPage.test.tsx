import { screen, waitFor } from '@testing-library/react'
import { axe } from 'jest-axe'
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
    let detailRequested = false
    server.use(
      http.get('*/api/v1/runs/:runName/graph/edges', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(graphEdges)
      }),
      http.get('*/api/v1/runs/:runName/graph/edges/:edgeId', () => {
        detailRequested = true
        return HttpResponse.json({
          ...graphEdges.items[0],
          evidence: [
            {
              evidence_id: 'evidence-create-list',
              relation_hint: 'response to parameter via test',
              source: 'final_graph',
              source_artifact_id: 'dependency_graph',
              value1: 'item.id',
              value2: 'itemId',
            },
          ],
        })
      }),
    )

    const { container } = renderWithProviders(
      <GraphPage
        runName="Run A"
        search={{
          edgeId: 'edge-create-list',
          edgeStatus: 'final',
          evidenceSource: 'final_graph',
          fromOperationId: 'post-/items',
          graphTab: 'edges',
          groupBy: 'from_node',
          limit: 10,
          offset: 0,
          q: 'items',
          toOperationId: 'get-/items',
        }}
      />,
    )

    await waitFor(() => expect(requestedUrl?.searchParams.get('from_operation_id')).toBe('post-/items'))
    expect(requestedUrl?.searchParams.get('to_operation_id')).toBe('get-/items')
    expect(requestedUrl?.searchParams.get('edge_status')).toBe('final')
    expect(requestedUrl?.searchParams.get('evidence_source')).toBe('final_graph')
    expect(requestedUrl?.searchParams.get('group_by')).toBe('from_node')
    expect(requestedUrl?.searchParams.get('limit')).toBe('10')
    expect(await screen.findByRole('dialog', { name: /edge detail/i })).toBeInTheDocument()
    expect(detailRequested).toBe(true)
    expect((await screen.findAllByText(/item\.id/)).length).toBeGreaterThan(0)

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('renders explorer-backed graph nodes and sequences with URL-backed sequence detail', async () => {
    renderWithProviders(
      <GraphPage
        runName="Run A"
        search={{
          graphTab: 'sequences',
          limit: 25,
          offset: 0,
          sequenceId: 'seq-create-list',
          sequenceType: 'dependency_chain',
        }}
      />,
    )

    expect(await screen.findByRole('tab', { name: /sequences/i })).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /graph sequences/i })).toBeInTheDocument()
    expect(await screen.findByRole('dialog', { name: /sequence detail/i })).toBeInTheDocument()
    expect(screen.getAllByText('dependency_chain').length).toBeGreaterThan(0)
  })
})

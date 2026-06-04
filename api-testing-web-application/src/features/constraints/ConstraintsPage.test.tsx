import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import {
  combinationEntries,
  combinationDetail,
  combinationReview,
  combinationReviewWithRunnableAndEvidence,
  constraintExplorerEntries,
  invariantExplorerEntries,
} from '../../test/fixtures'
import { server } from '../../test/msw/server'
import {
  setActivationOnboardingEventEmitter,
  type ActivationOnboardingEventEmitter,
} from '../product-tour/activationOnboardingAnalytics'
import App from '../../App'
import { ConstraintsPage } from './ConstraintsPage'
import { CombinationDetailComposer } from './components/CombinationDetailComposer'

describe('ConstraintsPage', () => {
  it('renders workbench by default with current-page triage and no accessibility violations', async () => {
    const { container } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /constraint workbench/i })).toBeInTheDocument()
    expect(screen.getByText(/what am i looking at/i)).toBeInTheDocument()
    expect(screen.getByText(/source tells you whether the signal came from static mining/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/constraint workspace summary/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/constraint workbench start here/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /top constraint signals/i })).toBeInTheDocument()
    expect(screen.getAllByText(/current page/i).length).toBeGreaterThan(0)
    await waitFor(() => expect(screen.getAllByText(/input.limit >= 1/i).length).toBeGreaterThan(0))
    expect(screen.getByRole('button', { name: /workbench/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /raw invariants/i })).toBeInTheDocument()

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  }, 10_000)

  it('renders the explorer table mode and maps URL-backed filters to explorer APIs', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/entries', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(constraintExplorerEntries)
      }),
    )

    const { container } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          agreementStatus: 'both_present',
          assertionAvailable: true,
          constraintId: 'constraint-limit',
          constraintKind: 'bounds',
          constraintTab: 'explorer',
          constraintsView: 'table',
          groupBy: 'source',
          limit: 10,
          offset: 0,
          operationId: 'get-/items',
          q: 'limit',
          source: 'combined',
        }}
      />,
    )

    await screen.findByRole('grid', { name: /constraint explorer entries/i })
    await screen.findByRole('complementary', { name: /constraint detail/i })
    expect(requestedUrl?.searchParams.get('agreement_status')).toBe('both_present')
    expect(requestedUrl?.searchParams.get('assertion_available')).toBe('true')
    expect(requestedUrl?.searchParams.get('constraint_kind')).toBe('bounds')
    expect(requestedUrl?.searchParams.get('source')).toBe('combined')
    expect(screen.getByRole('button', { name: /explorer/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText(/Minimum bound/i)).toBeInTheDocument()

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('renders invariant explorer entries and opens URL-backed invariant detail', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/invariants', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(invariantExplorerEntries)
      }),
    )

    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'invariants',
          constraintsView: 'table',
          invariantId: 'inv-limit',
          invariantKind: 'bounds',
          limit: 25,
          offset: 0,
          oracleReadiness: 'verified_runtime_oracle',
        }}
      />,
    )

    await screen.findByRole('grid', { name: /invariant explorer entries/i })
    expect(requestedUrl?.searchParams.get('invariant_kind')).toBe('bounds')
    expect(requestedUrl?.searchParams.get('oracle_readiness')).toBe('verified_runtime_oracle')
    expect(await screen.findByRole('complementary', { name: /invariant detail/i })).toBeInTheDocument()
    expect(screen.getAllByText('verified_runtime_oracle').length).toBeGreaterThan(0)
  })

  it('renders combination entries and opens sanitized combination detail', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(combinationEntries)
      }),
    )

    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          combinationId: 'cmb-limit',
          constraintTab: 'combination',
          constraintsView: 'table',
          hasRuntimeEvaluation: true,
          limit: 25,
          offset: 0,
          relation: 'EQUIVALENT',
          reviewState: 'PENDING_REVIEW',
          resolved: true,
          runtimeVerdict: 'BOTH_TRUE',
          status: 'RESOLVED',
          hasManualDecision: false,
        }}
      />,
    )

    expect(await screen.findByRole('grid', { name: /combination constraint entries/i })).toBeInTheDocument()
    expect(requestedUrl?.searchParams.get('relation')).toBe('EQUIVALENT')
    expect(requestedUrl?.searchParams.get('status')).toBe('RESOLVED')
    expect(requestedUrl?.searchParams.get('runtime_verdict')).toBe('BOTH_TRUE')
    expect(requestedUrl?.searchParams.get('resolved')).toBe('true')
    expect(requestedUrl?.searchParams.get('has_runtime_evaluation')).toBe('true')
    expect(requestedUrl?.searchParams.get('review_state')).toBe('PENDING_REVIEW')
    expect(requestedUrl?.searchParams.get('has_manual_decision')).toBe('false')
    expect(screen.getByRole('button', { name: /^combination$/i })).toHaveAttribute('aria-pressed', 'true')
    expect(await screen.findByRole('complementary', { name: /combination detail/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /constraint resolution/i })).toBeInTheDocument()
    expect(screen.getAllByText(/Equivalent/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Static and dynamic evidence agree/i)).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /human review preview/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open review workspace/i })).toHaveAttribute(
      'href',
      '/runs/Run%20A/constraints/combination/cmb-limit/review',
    )
  })

  it('shows Combination HITL activation on the table and marks eligible row selection', async () => {
    const user = userEvent.setup()
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries', () =>
        HttpResponse.json({
          ...combinationEntries,
          items: [
            {
              ...combinationEntries.items[0],
              combination_id: 'cmb-needs-review',
              relation: 'UNKNOWN',
              resolved: false,
              status: 'UNRESOLVED',
            },
          ],
        }),
      ),
    )

    const { store } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'combination',
          constraintsView: 'table',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('region', { name: /combination hitl activation/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /start hitl activation/i }))
    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.active).toBe(true)
    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.completedStepIds.open_combination_table).toBe(true)

    await user.click(screen.getByRole('checkbox', { name: /select cmb-needs-review for batch generation/i }))
    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.completedStepIds.select_eligible_row).toBe(true)
    expect(screen.getByText(/open the selected row preview/i)).toBeInTheDocument()
  })

  it('renders the dedicated combination review workspace route', async () => {
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId', () =>
        HttpResponse.json(combinationEntries.items[0]),
      ),
      http.get('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/review', () =>
        HttpResponse.json(combinationReviewWithRunnableAndEvidence),
      ),
    )
    window.history.pushState({}, '', '/runs/Run%20A/constraints/combination/cmb-limit/review')

    renderWithProviders(<App />)

    expect(await screen.findByRole('heading', { name: /combination review workspace/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /understand relation/i })).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /relation visual/i })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /relation semantics/i })).toBeInTheDocument()
    expect(screen.getByText(/raw enum/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/edit and approve draft cases/i)).length).toBeGreaterThan(0)
    expect(screen.getByRole('region', { name: /relation guide/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /run evidence readiness/i })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /runnable cases/i })).toBeInTheDocument()
    expect(screen.getByText(/http method risk/i)).toBeInTheDocument()
    expect(screen.getAllByText(/runtime evidence is support, not proof/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: /final decision support/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /accept static/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^finalize$/i })).toBeDisabled()
    expect(await screen.findByRole('textbox', { name: /request json ce-case-1/i })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /combination hitl activation/i })).toHaveTextContent(/4 of 7 complete/i)
  })

  it('separates runnable cases from executed evidence in the review workspace', async () => {
    renderWithProviders(
      <CombinationDetailComposer
        detail={{ ...combinationDetail, relation: 'DISJOINT', status: 'CONFLICT', resolved: false }}
        detailView="readable"
        evidenceLinks={[]}
        onApproveCase={() => undefined}
        onDetailViewChange={() => undefined}
        onFinalize={() => undefined}
        onGenerateDraft={() => undefined}
        onRejectCase={() => undefined}
        onReopen={() => undefined}
        onRunApproved={() => undefined}
        review={combinationReviewWithRunnableAndEvidence}
      />,
    )

    expect(await screen.findByRole('heading', { name: /run evidence readiness/i })).toBeInTheDocument()
    const runnableCases = await screen.findByRole('region', { name: /runnable cases/i })
    expect(within(runnableCases).getByText(/ce-case-approved-get/i)).toBeInTheDocument()
    expect(within(runnableCases).getByText(/ce-case-approved-delete/i)).toBeInTheDocument()
    expect(within(runnableCases).queryByText(/ce-case-executed/i)).not.toBeInTheDocument()
    expect(within(runnableCases).getAllByText(/delete has the highest mutation risk/i).length).toBeGreaterThan(0)

    const evidenceHistory = screen.getByRole('region', { name: /evidence history/i })
    expect(within(evidenceHistory).getByText(/ce-case-executed/i)).toBeInTheDocument()
    expect(within(evidenceHistory).getByText(/Conflict Both False/i)).toBeInTheDocument()
    expect(within(evidenceHistory).getByText(/support, not proof/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^run approved cases$/i })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /use https:\/\/example\.test/i }))
    fireEvent.click(screen.getByLabelText(/confirm unsafe http methods/i))
    expect(screen.getByRole('button', { name: /^run approved cases$/i })).toBeEnabled()
  }, 60_000)

  it('shows regenerate-required guidance for unsupported combination artifacts', async () => {
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries', () =>
        HttpResponse.json(
          {
            error: {
              code: 'invalid_request',
              message: 'Unsupported old-format combine_constraint_miners artifact. Regenerate required.',
            },
          },
          { status: 400 },
        ),
      ),
    )

    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'combination',
          constraintsView: 'table',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('alert', {}, { timeout: 5_000 })).toHaveTextContent(/regenerate required/i)
    expect(screen.getByText(/old-format combination artifact/i)).toBeInTheDocument()
  })

  it('sends HITL review mutation bodies with idempotency keys and edited draft request', async () => {
    const user = userEvent.setup()
    const requests: Record<string, unknown> = {}
    const activationEvents: Parameters<ActivationOnboardingEventEmitter>[0][] = []
    const restoreActivationEmitter = setActivationOnboardingEventEmitter((event) => activationEvents.push(event))
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId', () =>
        HttpResponse.json(combinationEntries.items[0]),
      ),
      http.get('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/review', () =>
        HttpResponse.json(combinationReview),
      ),
      http.post('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/counter-examples/generate', async ({ request }) => {
        requests.generate = await request.json()
        return HttpResponse.json(combinationReview)
      }),
      http.put('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/counter-examples/:caseId', async ({ request }) => {
        requests.update = await request.json()
        return HttpResponse.json({
          ...combinationReview,
          cases: combinationReview.cases.map((item) => ({ ...item, case_state: 'APPROVED' })),
          review_state: 'APPROVED',
        })
      }),
      http.post('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/review/finalize', async ({ request }) => {
        requests.finalize = await request.json()
        return HttpResponse.json({ ...combinationReview, review_state: 'FINAL_CONFIRMED' })
      }),
    )

    window.history.pushState({}, '', '/runs/Run%20A/constraints/combination/cmb-limit/review')
    const { store } = renderWithProviders(<App />)

    await screen.findByRole('heading', { name: /combination review workspace/i })
    expect(await screen.findByRole('button', { name: /use https:\/\/example\.test/i })).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /^generate draft$/i }))
    await waitFor(() => expect(requests.generate).toMatchObject({ live_llm: true }))
    expect((requests.generate as { idempotency_key: string }).idempotency_key).toMatch(/^generate-/)
    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.completedStepIds.generate_draft).toBe(true)

    const editor = await screen.findByRole('textbox', { name: /request json ce-case-1/i })
    fireEvent.change(editor, {
      target: { value: JSON.stringify({ method: 'GET', path: '/items', query: { limit: 7 } }) },
    })
    await user.click(screen.getByRole('button', { name: /approve draft/i }))
    await waitFor(() => expect(requests.update).toMatchObject({
      case_state: 'APPROVED',
      request: { method: 'GET', path: '/items', query: { limit: 7 } },
    }))
    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.completedStepIds.approve_case).toBe(true)

    await user.click(screen.getByRole('button', { name: /^accept static$/i }))
    await user.click(screen.getByRole('button', { name: /^finalize$/i }))
    expect(await screen.findByRole('dialog', { name: /finalize without runtime evidence/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /confirm finalize/i }))
    await waitFor(() => expect(requests.finalize).toMatchObject({ manual_decision: 'ACCEPT_STATIC' }))
    expect((requests.finalize as { idempotency_key: string }).idempotency_key).toMatch(/^finalize-/)
    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.completedStepIds.finalize_decision).toBe(true)
    expect(activationEvents.some((event) => event.type === 'activation_completed')).toBe(true)
    expect(JSON.stringify(activationEvents)).not.toContain('input.limit')
    expect(JSON.stringify(activationEvents)).not.toContain('cmb-limit')
    restoreActivationEmitter()
  }, 60_000)

  it('blocks approving draft requests that contain redacted executable values', async () => {
    const user = userEvent.setup()
    let updateCalled = false
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId', () =>
        HttpResponse.json(combinationEntries.items[0]),
      ),
      http.get('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/review', () =>
        HttpResponse.json(combinationReview),
      ),
      http.put('*/api/v1/runs/:runName/constraints/combination/entries/:combinationId/counter-examples/:caseId', async () => {
        updateCalled = true
        return HttpResponse.json(combinationReview)
      }),
    )

    window.history.pushState({}, '', '/runs/Run%20A/constraints/combination/cmb-limit/review')
    renderWithProviders(<App />)

    await screen.findByRole('heading', { name: /combination review workspace/i })
    const editor = await screen.findByRole('textbox', { name: /request json ce-case-1/i })
    fireEvent.change(editor, {
      target: {
        value: JSON.stringify({
          method: 'GET',
          path: '/items',
          query: { Session: '<REDACTED>' },
        }),
      },
    })
    await user.click(screen.getByRole('button', { name: /approve draft/i }))

    expect(await screen.findByText(/redacted executable values/i)).toBeInTheDocument()
    expect(updateCalled).toBe(false)

    fireEvent.change(editor, {
      target: {
        value: JSON.stringify({
          method: 'GET',
          path: '/items',
          headers: { Authorization: { type: 'redacted', reason: 'sensitive_header' } },
        }),
      },
    })
    await user.click(screen.getByRole('button', { name: /approve draft/i }))

    expect(await screen.findByText(/redacted executable values/i)).toBeInTheDocument()
    expect(updateCalled).toBe(false)
  }, 30_000)

  it('batch-generates counter-example drafts for selected eligible combination rows', async () => {
    const user = userEvent.setup()
    let requestBody: unknown
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/combination/entries', () =>
        HttpResponse.json({
          ...combinationEntries,
          items: [
            {
              ...combinationEntries.items[0],
              combination_id: 'cmb-needs-review',
              relation: 'UNKNOWN',
              resolved: false,
              status: 'UNRESOLVED',
            },
            {
              ...combinationEntries.items[0],
              combination_id: 'cmb-resolved',
              relation: 'EQUIVALENT',
              resolved: true,
              status: 'RESOLVED',
            },
          ],
          pagination: { limit: 25, offset: 0, total: 2 },
        }),
      ),
      http.post('*/api/v1/runs/:runName/constraints/combination/counter-examples/batch-generate', async ({ request }) => {
        requestBody = await request.json()
        return HttpResponse.json({
          results: [
            {
              case_count: 1,
              combination_id: 'cmb-limit',
              message: 'Draft generated',
              new_case_count: 1,
              status: 'generated',
              total_case_count: 2,
            },
          ],
        })
      }),
    )

    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'combination',
          constraintsView: 'table',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    await screen.findByRole('grid', { name: /combination constraint entries/i })
    const batchButton = screen.getByRole('button', { name: /batch generate drafts/i })
    expect(batchButton).toBeDisabled()
    expect(screen.getByText(/select eligible rows to generate drafts/i)).toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: /select cmb-needs-review for batch generation/i }))
    await user.click(screen.getByRole('checkbox', { name: /select cmb-resolved for batch generation/i }))
    await waitFor(() => expect(batchButton).toBeEnabled())
    await user.click(batchButton)
    const confirmDialog = await screen.findByRole('dialog', { name: /confirm live draft generation/i })
    expect(confirmDialog).toBeInTheDocument()
    expect(within(confirmDialog).getByText(/2 selected rows/i)).toBeInTheDocument()
    expect(within(confirmDialog).getByText(/1 eligible/i)).toBeInTheDocument()
    expect(within(confirmDialog).getByText(/1 skipped/i)).toBeInTheDocument()
    expect(within(confirmDialog).getByText(/live llm draft generation can add latency and provider cost/i)).toBeInTheDocument()
    const liveToggle = within(confirmDialog).getByRole('checkbox', { name: /use live llm for selected rows/i })
    expect(liveToggle).toBeChecked()
    await user.click(liveToggle)
    await user.click(screen.getByRole('button', { name: /confirm live generation/i }))
    await waitFor(() => expect(requestBody).toMatchObject({
      combination_ids: ['cmb-needs-review'],
      live_llm: false,
      max_cases_per_item: 3,
    }))
    expect((requestBody as { idempotency_key: string }).idempotency_key).toMatch(/^batch-generate-/)
    expect(screen.getByText(/generated 1 new draft for 1 row \(2 total\)/i)).toBeInTheDocument()
  })

  it('shows manual decision and effective final context in Constraint Explorer rows', async () => {
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/entries', () =>
        HttpResponse.json({
          ...constraintExplorerEntries,
          items: [
            {
              ...constraintExplorerEntries.items[0],
              decision_source: 'manual',
              has_manual_decision: true,
              manual_decision: 'NO_FINAL',
              manual_final_constraint: null,
              review_state: 'FINAL_CONFIRMED',
            },
            {
              ...constraintExplorerEntries.items[0],
              constraint_id: 'constraint-manual-final',
              decision_source: 'manual',
              expression: 'input.limit <= 100',
              has_manual_decision: true,
              manual_decision: 'CUSTOM_FINAL',
              manual_final_constraint: 'input.limit <= 100',
              review_state: 'FINAL_CONFIRMED',
            },
          ],
          pagination: { limit: 25, offset: 0, total: 2 },
        }),
      ),
    )

    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'table',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('grid', { name: /constraint explorer entries/i })).toBeInTheDocument()
    expect(screen.getAllByText(/Human: No Final/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/No effective final/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Human: Custom Final/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Effective final: input\.limit <= 100/i)).toBeInTheDocument()
  })

  it('renders static, dynamic, and invariant query results with groups', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'static',
          constraintsView: 'table',
          groupBy: 'section',
          limit: 25,
          offset: 0,
          q: 'limit',
          sortBy: 'operation_id',
          sortOrder: 'asc',
        }}
      />,
    )

    expect(await screen.findByText('input.limit >= 1')).toBeInTheDocument()
    expect(screen.getAllByText(/request_response/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /dynamic/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /raw invariants/i })).toBeInTheDocument()
  })

  it('exposes URL-backed filters, advanced group chips, row detail, and operation drawer', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'static',
          constraintsView: 'table',
          groupBy: 'section',
          limit: 10,
          offset: 0,
          operationId: 'get-/items',
          q: 'limit',
          section: 'request_response',
          sortBy: 'property_path',
          sortOrder: 'asc',
        }}
      />,
    )

    expect(await screen.findByDisplayValue('get-/items')).toBeInTheDocument()
    expect(screen.getByDisplayValue('request_response')).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /static constraint entries/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /advanced filters/i }))
    expect(await screen.findByRole('dialog', { name: /advanced constraint filters/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /request_response \(1\)/i }))
    expect(window.location.search).toContain('section=request_response')
    await user.click(screen.getByRole('button', { name: /^done$/i }))

    expect(await screen.findByRole('complementary', { name: /operation detail/i })).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: /input.limit >= 1/i })[0])
    expect(await screen.findByRole('complementary', { name: /constraint detail/i })).toBeInTheDocument()
  })

  it('renders matrix mode for oracle readiness triage', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'matrix',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /readiness matrix/i })).toBeInTheDocument()
    expect(screen.getAllByText(/current page/i).length).toBeGreaterThan(0)
    await waitFor(() => expect(screen.getAllByText(/both_present/i).length).toBeGreaterThan(0))
    expect(screen.getByText(/assertion evidence/i)).toBeInTheDocument()
  })

  it('keeps primary filters URL-backed while clear filters resets query state', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
          q: 'limit',
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /constraint workbench/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /combined 1/i }))
    expect(window.location.search).toContain('source=combined')

    await user.clear(screen.getByRole('textbox', { name: /search constraints/i }))
    await user.type(screen.getByRole('textbox', { name: /search constraints/i }), 'date')
    await user.tab()
    expect(window.location.search).toContain('q=date')

    await user.click(screen.getByRole('button', { name: /clear filters/i }))
    expect(window.location.search).not.toContain('q=')
    expect(window.location.search).not.toContain('source=')
  })

  it('switches top segmented modes through URL-backed params', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    await screen.findByRole('heading', { name: /constraint workbench/i })
    await user.click(screen.getByRole('button', { name: /^Explorer$/i }))

    expect(window.location.search).toContain('constraintsView=table')
    expect(window.location.search).toContain('constraintTab=explorer')
  })

  it('renders readable constraint detail by default and raw fields when requested', async () => {
    const { rerender } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintId: 'constraint-limit',
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('complementary', { name: /constraint detail/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /how to read this/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /source lineage/i })).toBeInTheDocument()
    expect(screen.getByText(/Text matches static expression/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Minimum bound/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /raw fields/i })).toBeInTheDocument()

    rerender(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintDetailView: 'raw',
          constraintId: 'constraint-limit',
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByLabelText(/constraint raw fields/i)).toBeInTheDocument()
  })

  it('renders readable invariant evidence detail', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'invariants',
          constraintsView: 'table',
          invariantId: 'inv-limit',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('complementary', { name: /invariant detail/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /correlation evidence/i })).toBeInTheDocument()
    expect(screen.getByText(/property path matched input.limit/i)).toBeInTheDocument()
    expect(screen.getByText(/Minimum bound/i)).toBeInTheDocument()
  })
})

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { harEntries } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { HistoryPage } from './HistoryPage'

describe('HistoryPage', () => {
  it('renders HAR sessions, entries, and redaction markers', async () => {
    renderWithProviders(<HistoryPage runName="Run A" search={{ includeBody: false, limit: 25, offset: 0 }} />)

    expect((await screen.findAllByText('session-1')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('entry-1')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('<REDACTED>')).length).toBeGreaterThan(0)
  })

  it('opens URL-backed HAR entry detail and clears stale entry selection when session changes', async () => {
    const user = userEvent.setup()
    window.history.replaceState({}, '', '/runs/Run%20A/history?sessionId=session-1&entryId=entry-1')
    server.use(
      http.get('*/api/v1/runs/:runName/history/sessions', () =>
        HttpResponse.json({
          run_name: 'Run A',
          sessions: [
            { entry_count: 1, modified_at: '2026-01-01T00:00:00Z', session_id: 'session-1', size_bytes: 1024 },
            { entry_count: 1, modified_at: '2026-01-02T00:00:00Z', session_id: 'session-2', size_bytes: 2048 },
          ],
        }),
      ),
      http.get('*/api/v1/runs/:runName/history/sessions/:sessionId/entries', () =>
        HttpResponse.json(harEntries),
      ),
    )

    renderWithProviders(
      <HistoryPage
        runName="Run A"
        search={{ entryId: 'entry-1', includeBody: false, limit: 25, offset: 0, sessionId: 'session-1' }}
      />,
    )

    expect(await screen.findByRole('dialog', { name: /har entry detail/i })).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /session-2/i }))

    expect(window.location.search).toContain('sessionId=session-2')
    expect(window.location.search).not.toContain('entryId=')
  })
})

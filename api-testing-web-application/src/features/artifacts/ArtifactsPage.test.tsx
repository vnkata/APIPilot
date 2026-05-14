import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithProviders } from '../../test/renderWithProviders'
import { ArtifactsPage } from './ArtifactsPage'

describe('ArtifactsPage', () => {
  it('renders artifact catalog and lazy raw viewer for selected artifact', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ArtifactsPage runName="Run A" search={{ artifactId: 'specification', compare: false, raw: true }} />,
    )

    expect((await screen.findAllByText('specification')).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/raw_json/i).length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: /summary/i }))
    expect(screen.getAllByText(/summary/i).length).toBeGreaterThan(0)
  })

  it('renders compare mode and exports only visible sanitized artifact data', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ArtifactsPage runName="Run A" search={{ artifactId: 'specification', compare: true, raw: false }} />,
    )

    expect((await screen.findAllByText(/compare summary and raw/i)).length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: /export snapshot/i }))
    expect(await screen.findByRole('dialog', { name: /export snapshot/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/export preview/i)).toHaveTextContent('specification')
    expect(screen.getByLabelText(/export preview/i)).not.toHaveTextContent('test-response-token')
  })

  it('renders raw CSV artifacts as a scan-friendly table', async () => {
    renderWithProviders(
      <ArtifactsPage runName="Run A" search={{ artifactId: 'invariants_csv', compare: false, raw: true }} />,
    )

    expect(await screen.findByRole('table', { name: /csv preview/i })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'pptname' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'return.items.id >= 1' })).toBeInTheDocument()
  })
})

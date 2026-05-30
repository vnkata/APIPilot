import { act, fireEvent, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../../test/renderWithProviders'
import { DebouncedTextField } from './DebouncedTextField'

describe('DebouncedTextField', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('commits text after the debounce delay', () => {
    const onDebouncedChange = vi.fn()
    renderWithProviders(
      <DebouncedTextField
        label="Search operations"
        onDebouncedChange={onDebouncedChange}
        value=""
      />,
    )

    fireEvent.change(screen.getByRole('textbox', { name: /search operations/i }), {
      target: { value: 'items' },
    })

    expect(onDebouncedChange).not.toHaveBeenCalled()
    act(() => vi.advanceTimersByTime(350))
    expect(onDebouncedChange).toHaveBeenCalledWith('items')
  })

  it('commits text immediately on Enter', () => {
    const onDebouncedChange = vi.fn()
    renderWithProviders(
      <DebouncedTextField
        label="Search operations"
        onDebouncedChange={onDebouncedChange}
        value=""
      />,
    )

    const input = screen.getByRole('textbox', { name: /search operations/i })
    fireEvent.change(input, { target: { value: 'items' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onDebouncedChange).toHaveBeenCalledWith('items')
  })
})

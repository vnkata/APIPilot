import { TextField, type TextFieldProps } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

type DebouncedTextFieldProps = Omit<TextFieldProps, 'onChange' | 'value'> & {
  delay?: number
  onDebouncedChange: (value: string) => void
  value?: string
}

export function DebouncedTextField({
  delay = 350,
  onDebouncedChange,
  onKeyDown,
  value = '',
  ...props
}: DebouncedTextFieldProps) {
  const [{ draft, propValue }, setDraftState] = useState({ draft: value, propValue: value })
  const onDebouncedChangeRef = useRef(onDebouncedChange)

  if (propValue !== value) {
    setDraftState({ draft: value, propValue: value })
  }

  useEffect(() => {
    onDebouncedChangeRef.current = onDebouncedChange
  }, [onDebouncedChange])

  useEffect(() => {
    if (draft === value) return undefined

    const timeout = window.setTimeout(() => {
      onDebouncedChangeRef.current(draft)
    }, delay)

    return () => window.clearTimeout(timeout)
  }, [delay, draft, value])

  function commitDraft() {
    if (draft !== value) {
      onDebouncedChangeRef.current(draft)
    }
  }

  return (
    <TextField
      {...props}
      onBlur={(event) => {
        commitDraft()
        props.onBlur?.(event)
      }}
      onChange={(event) => setDraftState({ draft: event.target.value, propValue: value })}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          commitDraft()
        }
        onKeyDown?.(event)
      }}
      value={draft}
    />
  )
}

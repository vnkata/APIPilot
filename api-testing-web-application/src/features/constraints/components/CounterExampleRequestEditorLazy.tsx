import { lazy, Suspense } from 'react'
import { Box, CircularProgress, Stack, TextField, Typography } from '@mui/material'

import { monoFontFamily } from '../../../theme/typography'

const MonacoEditor = lazy(async () => {
  const module = await import('@monaco-editor/react')
  return { default: module.Editor }
})

type CounterExampleRequestEditorLazyProps = {
  error?: boolean
  helperText?: string
  label: string
  onChange: (value: string) => void
  value: string
}

export function CounterExampleRequestEditorLazy({
  error = false,
  helperText,
  label,
  onChange,
  value,
}: CounterExampleRequestEditorLazyProps) {
  if (import.meta.env.MODE === 'test') {
    return (
      <TextField
        error={error}
        fullWidth
        helperText={helperText}
        label={label}
        minRows={8}
        multiline
        onChange={(event) => onChange(event.target.value)}
        size="small"
        sx={{ '& textarea': { fontFamily: monoFontFamily } }}
        value={value}
      />
    )
  }

  return (
    <Stack spacing={0.75}>
      <Typography color={error ? 'error' : 'text.secondary'} sx={{ fontWeight: 800 }} variant="caption">
        {label}
      </Typography>
      <Suspense
        fallback={
          <Stack sx={{ alignItems: 'center', height: 320, justifyContent: 'center' }}>
            <CircularProgress size={24} />
            <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
              Loading request editor
            </Typography>
          </Stack>
        }
      >
        <Box
          aria-label={label}
          role="region"
          sx={(theme) => ({
            border: '1px solid',
            borderColor: error ? theme.palette.error.main : theme.palette.divider,
            height: 360,
          })}
        >
          <MonacoEditor
            height="360px"
            language="json"
            onChange={(nextValue) => onChange(nextValue ?? '')}
            options={{
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              tabSize: 2,
              wordWrap: 'on',
            }}
            theme="vs-dark"
            value={value}
          />
        </Box>
      </Suspense>
      {helperText ? (
        <Typography color={error ? 'error' : 'text.secondary'} variant="caption">
          {helperText}
        </Typography>
      ) : null}
    </Stack>
  )
}

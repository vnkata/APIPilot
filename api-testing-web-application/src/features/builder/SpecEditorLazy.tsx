import { lazy, Suspense } from 'react'
import { Box, CircularProgress, Stack, Typography } from '@mui/material'

const MonacoEditor = lazy(async () => {
  const module = await import('@monaco-editor/react')
  return { default: module.Editor }
})

type SpecEditorLazyProps = {
  language: string
  onChange: (value: string) => void
  value: string
}

export function SpecEditorLazy({ language, onChange, value }: SpecEditorLazyProps) {
  if (import.meta.env.MODE === 'test') {
    return (
      <textarea
        aria-label="advanced spec editor"
        onChange={(event) => onChange(event.target.value)}
        style={{ minHeight: 280, width: '100%' }}
        value={value}
      />
    )
  }

  return (
    <Suspense
      fallback={
        <Stack sx={{ alignItems: 'center', height: 280, justifyContent: 'center' }}>
          <CircularProgress size={24} />
          <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
            Loading spec editor
          </Typography>
        </Stack>
      }
    >
      <Box
        aria-label="advanced spec editor"
        role="region"
        sx={{ border: '1px solid', borderColor: 'divider', height: 360 }}
      >
        <MonacoEditor
          height="360px"
          language={language}
          onChange={(nextValue) => onChange(nextValue ?? '')}
          options={{
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
          }}
          theme="vs-dark"
          value={value}
        />
      </Box>
    </Suspense>
  )
}

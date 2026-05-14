import { lazy, Suspense } from 'react'
import { Box, CircularProgress, Stack, Typography } from '@mui/material'

import { JsonBlock } from '../../shared/ui/JsonBlock'

const MonacoEditor = lazy(async () => {
  const module = await import('@monaco-editor/react')
  return { default: module.Editor }
})

const MonacoDiffEditor = lazy(async () => {
  const module = await import('@monaco-editor/react')
  return { default: module.DiffEditor }
})

type CodeViewerLazyProps = {
  language: string
  value: string
}

type DiffViewerLazyProps = {
  language: string
  modified: string
  original: string
}

export function CodeViewerLazy({ language, value }: CodeViewerLazyProps) {
  if (import.meta.env.MODE === 'test') {
    return <JsonBlock ariaLabel="artifact raw content" maxHeight={520} value={value} />
  }

  return (
    <Suspense
      fallback={
        <Stack sx={{ alignItems: 'center', height: 360, justifyContent: 'center' }}>
          <CircularProgress size={24} />
          <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
            Loading code viewer
          </Typography>
        </Stack>
      }
    >
      <Box
        aria-label="artifact raw content"
        role="region"
        sx={{ border: '1px solid', borderColor: 'divider', height: 520 }}
      >
        <MonacoEditor
          height="520px"
          language={language}
          options={{
            minimap: { enabled: true },
            readOnly: true,
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

export function DiffViewerLazy({ language, modified, original }: DiffViewerLazyProps) {
  if (import.meta.env.MODE === 'test') {
    return (
      <Stack spacing={1}>
        <Typography variant="subtitle2">Compare summary and raw</Typography>
        <JsonBlock
          ariaLabel="artifact diff content"
          maxHeight={520}
          value={{ modified, original }}
        />
      </Stack>
    )
  }

  return (
    <Suspense
      fallback={
        <Stack sx={{ alignItems: 'center', height: 420, justifyContent: 'center' }}>
          <CircularProgress size={24} />
          <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
            Loading diff viewer
          </Typography>
        </Stack>
      }
    >
      <Box
        aria-label="artifact diff content"
        role="region"
        sx={{ border: '1px solid', borderColor: 'divider', height: 520 }}
      >
        <MonacoDiffEditor
          height="520px"
          language={language}
          modified={modified}
          options={{
            minimap: { enabled: true },
            readOnly: true,
            renderSideBySide: true,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
          }}
          original={original}
          theme="vs-dark"
        />
      </Box>
    </Suspense>
  )
}

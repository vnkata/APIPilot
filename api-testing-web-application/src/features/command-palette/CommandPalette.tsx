import SearchIcon from '@mui/icons-material/Search'
import {
  Box,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useState } from 'react'

import { useArtifacts } from '../artifacts/api'
import { useOperationExplorerEntries } from '../operations/api'
import { encodeRoutePart } from '../../shared/lib/format'
import { navigateInApp } from '../../shared/lib/navigation'

type CommandPaletteProps = {
  runName?: string
}

type CommandItem = {
  href: string
  label: string
  section: string
  subtitle?: string
}

function matchesCommand(command: CommandItem, query: string) {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return true

  return [command.label, command.section, command.subtitle]
    .filter(Boolean)
    .some((value) => value?.toLowerCase().includes(normalizedQuery))
}

export function CommandPalette({ runName }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const encodedRunName = runName ? encodeRoutePart(runName) : undefined
  const operationsQuery = useOperationExplorerEntries(
    runName ?? '',
    { limit: 8, offset: 0 },
    { query: { enabled: open && Boolean(runName) } },
  )
  const artifactsQuery = useArtifacts(runName ?? '', {
    query: { enabled: open && Boolean(runName) },
  })

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const commands = useMemo<CommandItem[]>(() => {
    const globalCommands: CommandItem[] = [
      { href: '/runs', label: 'Runs catalog', section: 'Navigation', subtitle: 'Open local artifact runs' },
      { href: '/compare', label: 'Compare runs', section: 'Navigation', subtitle: 'Diff summaries and artifacts' },
    ]

    if (!encodedRunName) return globalCommands

    return [
      ...globalCommands,
      { href: `/runs/${encodedRunName}`, label: 'Run overview', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/operations`, label: 'Operations explorer', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/graph`, label: 'Dependency graph', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/constraints`, label: 'Constraints workbench', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/artifacts`, label: 'Artifact workbench', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/reports`, label: 'Reports', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/test-cases`, label: 'Test cases', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/history`, label: 'HTTP history', section: 'Current run', subtitle: runName },
      ...(operationsQuery.data?.items ?? []).map((operation) => ({
        href: `/runs/${encodedRunName}/operations?operationKey=${encodeURIComponent(operation.operation_key)}`,
        label: operation.display_operation_id ?? operation.operation_id,
        section: 'Operations',
        subtitle: `${(operation.http_method ?? 'GET').toUpperCase()} ${operation.path_template ?? operation.operation_id}`,
      })),
      ...(artifactsQuery.data?.artifacts ?? []).map((artifact) => ({
        href: `/runs/${encodedRunName}/artifacts?artifactId=${encodeURIComponent(artifact.artifact_id)}`,
        label: artifact.artifact_id,
        section: 'Artifacts',
        subtitle: `${artifact.kind} · ${artifact.raw_policy}`,
      })),
    ]
  }, [artifactsQuery.data?.artifacts, encodedRunName, operationsQuery.data?.items, runName])

  const visibleCommands = commands.filter((command) => matchesCommand(command, query)).slice(0, 12)

  function runCommand(command: CommandItem) {
    navigateInApp(command.href)
    setOpen(false)
    setQuery('')
  }

  return (
    <>
      <Tooltip title="Command palette">
        <IconButton aria-label="Open command palette" onClick={() => setOpen(true)} size="small">
          <SearchIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog
        aria-labelledby="command-palette-title"
        fullWidth
        maxWidth="md"
        onClose={() => setOpen(false)}
        open={open}
      >
        <DialogTitle id="command-palette-title">Command palette</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <TextField
              autoFocus
              fullWidth
              label="Search commands"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Navigate, operation, artifact..."
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
              value={query}
            />
            <List aria-label="Command results" dense disablePadding>
              {visibleCommands.map((command) => (
                <ListItemButton
                  key={`${command.section}:${command.href}:${command.label}`}
                  onClick={() => runCommand(command)}
                  sx={{ borderRadius: 1 }}
                >
                  <ListItemText
                    primary={
                      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                        <Typography sx={{ fontWeight: 700 }} variant="body2">
                          {command.label}
                        </Typography>
                        <Chip label={command.section} size="small" variant="outlined" />
                      </Stack>
                    }
                    secondary={command.subtitle}
                  />
                </ListItemButton>
              ))}
              {visibleCommands.length === 0 ? (
                <Box sx={{ p: 2 }}>
                  <Typography color="text.secondary" variant="body2">
                    No matching commands.
                  </Typography>
                </Box>
              ) : null}
            </List>
          </Stack>
        </DialogContent>
      </Dialog>
    </>
  )
}

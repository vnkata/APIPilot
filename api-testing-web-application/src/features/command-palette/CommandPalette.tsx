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
import { useCallback, useEffect, useMemo, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'

import { useArtifacts } from '../artifacts/api'
import { useOperationExplorerEntries } from '../operations/api'
import { encodeRoutePart } from '../../shared/lib/format'
import { navigateInApp } from '../../shared/lib/navigation'
import {
  loadBookmarks,
  loadRecentEntities,
  loadSavedViews,
  type RecentEntity,
  type SavedView,
  type WorkspaceBookmark,
} from '../../shared/lib/workspaceStorage'

type CommandPaletteProps = {
  runName?: string
}

type CommandItem = {
  action?: () => void
  href: string
  label: string
  section: string
  subtitle?: string
}

function fuzzyScore(value: string, query: string) {
  const normalizedValue = value.toLowerCase()
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return 1
  if (normalizedValue.includes(normalizedQuery)) return 100 - normalizedValue.indexOf(normalizedQuery)

  let queryIndex = 0
  let score = 0
  let lastMatchIndex = -1
  for (let valueIndex = 0; valueIndex < normalizedValue.length && queryIndex < normalizedQuery.length; valueIndex += 1) {
    if (normalizedValue[valueIndex] === normalizedQuery[queryIndex]) {
      score += lastMatchIndex === valueIndex - 1 ? 6 : 3
      lastMatchIndex = valueIndex
      queryIndex += 1
    }
  }

  return queryIndex === normalizedQuery.length ? score : -1
}

function commandScore(command: CommandItem, query: string) {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return 1

  return [command.label, command.section, command.subtitle]
    .filter(Boolean)
    .reduce((bestScore, value) => Math.max(bestScore, fuzzyScore(value ?? '', normalizedQuery)), -1)
}

export function CommandPalette({ runName }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [savedViews, setSavedViews] = useState<SavedView[]>([])
  const [bookmarks, setBookmarks] = useState<WorkspaceBookmark[]>([])
  const [recentEntities, setRecentEntities] = useState<RecentEntity[]>([])
  const encodedRunName = runName ? encodeRoutePart(runName) : undefined
  const operationsQuery = useOperationExplorerEntries(
    runName ?? '',
    { limit: 8, offset: 0 },
    { query: { enabled: open && Boolean(runName) } },
  )
  const artifactsQuery = useArtifacts(runName ?? '', {
    query: { enabled: open && Boolean(runName) },
  })

  const openPalette = useCallback(() => {
    setSavedViews(loadSavedViews())
    setBookmarks(loadBookmarks())
    setRecentEntities(loadRecentEntities())
    setActiveIndex(0)
    setOpen(true)
  }, [])

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        openPalette()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [openPalette])

  function closePalette() {
    setOpen(false)
    setQuery('')
    setActiveIndex(0)
  }

  function updateQuery(value: string) {
    setQuery(value)
    setActiveIndex(0)
  }

  const commands = useMemo<CommandItem[]>(() => {
    const globalCommands: CommandItem[] = [
      { href: '/runs', label: 'Runs catalog', section: 'Navigation', subtitle: 'Open local artifact runs' },
      { href: '/builder/specs', label: 'Run Builder', section: 'Navigation', subtitle: 'Upload specs and create APIPilot executions' },
      { href: '/builder/executions', label: 'Execution Center', section: 'Navigation', subtitle: 'Track write-flow execution lifecycle' },
      { href: '/compare', label: 'Compare runs', section: 'Navigation', subtitle: 'Diff summaries and artifacts' },
    ]

    if (!encodedRunName) return globalCommands

    return [
      ...globalCommands,
      { href: `/runs/${encodedRunName}`, label: 'Run overview', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/workspace`, label: 'Workspace cockpit', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/operations`, label: 'Operations explorer', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/graph`, label: 'Dependency graph', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/constraints`, label: 'Constraints workbench', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/artifacts`, label: 'Artifact workbench', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/reports`, label: 'Reports', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/test-cases`, label: 'Test cases', section: 'Current run', subtitle: runName },
      { href: `/runs/${encodedRunName}/history`, label: 'HTTP history', section: 'Current run', subtitle: runName },
      {
        href: `/compare?leftRun=${encodeURIComponent(runName ?? '')}`,
        label: 'Open current run in Compare',
        section: 'Compare',
        subtitle: 'Open selected compare context for the current run',
      },
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
      ...(artifactsQuery.data?.artifacts ?? []).map((artifact) => ({
        href: `/compare?leftRun=${encodeURIComponent(runName ?? '')}&artifactId=${encodeURIComponent(artifact.artifact_id)}`,
        label: `Compare ${artifact.artifact_id}`,
        section: 'Artifacts',
        subtitle: 'Open in Compare Lab',
      })),
      ...savedViews
        .filter((view) => view.runName === runName)
        .map((view) => ({
          href: view.route,
          label: view.name,
          section: 'Saved views',
          subtitle: `${view.page} · ${view.runName}`,
        })),
      ...bookmarks
        .filter((bookmark) => bookmark.runName === runName)
        .map((bookmark) => ({
          href: bookmark.href,
          label: bookmark.label,
          section: 'Bookmarks',
          subtitle: bookmark.entityType,
        })),
      ...recentEntities
        .filter((entity) => entity.runName === runName)
        .map((entity) => ({
          href: entity.href,
          label: entity.label,
          section: 'Recent entities',
          subtitle: `${entity.entityType} · ${entity.source}`,
        })),
    ]
  }, [
    artifactsQuery.data?.artifacts,
    bookmarks,
    encodedRunName,
    operationsQuery.data?.items,
    recentEntities,
    runName,
    savedViews,
  ])

  const visibleCommands = useMemo(
    () =>
      commands
        .map((command) => ({ command, score: commandScore(command, query) }))
        .filter((item) => item.score >= 0)
        .sort((a, b) => b.score - a.score || a.command.section.localeCompare(b.command.section))
        .slice(0, 12)
        .map((item) => item.command),
    [commands, query],
  )

  function runCommand(command: CommandItem) {
    command.action?.()
    navigateInApp(command.href)
    closePalette()
  }

  function handleInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      closePalette()
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, visibleCommands.length - 1))
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
      return
    }

    if (event.key === 'Enter' && visibleCommands[activeIndex]) {
      event.preventDefault()
      runCommand(visibleCommands[activeIndex])
    }
  }

  return (
    <>
      <Tooltip title="Command palette">
        <IconButton aria-label="Open command palette" onClick={openPalette} size="small">
          <SearchIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog
        aria-labelledby="command-palette-title"
        fullWidth
        maxWidth="md"
        onClose={closePalette}
        open={open}
      >
        <DialogTitle id="command-palette-title">Command palette</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <TextField
              autoFocus
              fullWidth
              label="Search commands"
              onChange={(event) => updateQuery(event.target.value)}
              onKeyDown={handleInputKeyDown}
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
              {visibleCommands.map((command, index) => (
                <ListItemButton
                  key={`${command.section}:${command.href}:${command.label}`}
                  onClick={() => runCommand(command)}
                  selected={index === activeIndex}
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

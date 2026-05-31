import AddIcon from '@mui/icons-material/Add'
import PreviewIcon from '@mui/icons-material/Preview'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import type { SpecMetadataResponse } from '../../shared/api/generated/model'
import { normalizeApiError } from '../../shared/api/errors'
import { PageHeader } from '../../shared/ui/PageHeader'
import { GuidanceCallout } from '../../shared/ui/Guidance'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import { builderQueryKeys, useCreateSpec, useSpecs } from './api'
import { builderPath, encodePathPart } from './builderUtils'
import { SpecEditorLazy } from './SpecEditorLazy'

function detectLanguage(filename: string) {
  return /\.ya?ml$/i.test(filename) ? 'yaml' : 'json'
}

function UploadSpecDialog({ onClose, open }: { onClose: () => void; open: boolean }) {
  const queryClient = useQueryClient()
  const [filename, setFilename] = useState('')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const createSpec = useCreateSpec({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: builderQueryKeys.specs() })
        onClose()
        setFilename('')
        setTitle('')
        setContent('')
        setAdvancedOpen(false)
      },
    },
  })
  const error = createSpec.error ? normalizeApiError(createSpec.error) : undefined

  async function handleFile(file: File | undefined) {
    if (!file) return
    setFilename(file.name)
    setContent(await file.text())
  }

  function handleCreate() {
    if (!filename || !content) return
    createSpec.mutate({
      data: {
        content,
        filename,
        title: title.trim() || undefined,
      },
    })
  }

  return (
    <Dialog fullWidth maxWidth="md" onClose={onClose} open={open}>
      <DialogTitle>Upload OpenAPI spec</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Button component="label" startIcon={<UploadFileIcon />} variant="outlined">
            Choose OpenAPI file
            <input
              accept=".json,.yaml,.yml,application/json,text/yaml,text/x-yaml"
              aria-label="OpenAPI file"
              hidden
              onChange={(event) => void handleFile(event.target.files?.[0])}
              type="file"
            />
          </Button>
          {filename ? (
            <Typography color="text.secondary" variant="body2">
              Selected: {filename}
            </Typography>
          ) : null}
          <TextField label="Title" onChange={(event) => setTitle(event.target.value)} value={title} />
          <TextField
            aria-label="spec content"
            label="Spec content"
            minRows={8}
            multiline
            onChange={(event) => setContent(event.target.value)}
            placeholder="Paste OpenAPI JSON or YAML"
            value={content}
          />
          <FormControlLabel
            control={<Switch checked={advancedOpen} onChange={(event) => setAdvancedOpen(event.target.checked)} />}
            label="Advanced raw editor"
          />
          {advancedOpen ? (
            <SpecEditorLazy
              language={detectLanguage(filename)}
              onChange={setContent}
              value={content}
            />
          ) : null}
          {error ? <Alert severity="error">{error.message}</Alert> : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          disabled={!filename || !content || createSpec.isPending}
          onClick={handleCreate}
          startIcon={<AddIcon />}
          variant="contained"
        >
          Create spec
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export function SpecsPage() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const specsQuery = useSpecs()
  const rows = specsQuery.data?.specs ?? []
  const columns = useMemo<GridColDef<SpecMetadataResponse>[]>(
    () => [
      {
        field: 'title',
        flex: 1,
        headerName: 'Title',
        minWidth: 180,
      },
      {
        field: 'filename',
        flex: 1,
        headerName: 'Filename',
        minWidth: 180,
      },
      {
        field: 'operation_count',
        headerName: 'Operations',
        minWidth: 120,
      },
      {
        field: 'created_at',
        headerName: 'Created',
        minWidth: 180,
      },
      {
        field: 'actions',
        headerName: 'Actions',
        minWidth: 180,
        sortable: false,
        renderCell: (params) => (
          <Button
            component="a"
            href={builderPath(`/specs/${encodePathPart(params.row.spec_id)}`)}
            size="small"
            startIcon={<PreviewIcon />}
          >
            Preview operations
          </Button>
        ),
      },
    ],
    [],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button
            onClick={() => setUploadOpen(true)}
            startIcon={<UploadFileIcon />}
            variant="contained"
            {...tourAnchor(TOUR_ANCHORS.builderSpecsUpload)}
          >
            Upload spec
          </Button>
        }
        eyebrow="Builder"
        subtitle="Upload OpenAPI JSON or YAML and preview operations before creating APIPilot run configs."
        title="Spec Manager"
        {...tourAnchor(TOUR_ANCHORS.builderSpecsHeader)}
      />
      <GuidanceCallout
        bullets={[
          'Upload the OpenAPI document first.',
          'Preview operations before creating a run config.',
          'Use dry-run execution unless you intentionally need live target traffic.',
        ]}
        title="Builder workflow"
      />
      <QueryState
        empty={rows.length === 0}
        emptyDescription="Upload an OpenAPI spec to start a new APIPilot run."
        emptyTitle="No uploaded specs"
        error={specsQuery.error}
        isError={specsQuery.isError}
        isLoading={specsQuery.isLoading}
        onRetry={() => void specsQuery.refetch()}
      >
        <ServerDataGridPanel
          ariaLabel="uploaded specs"
          columns={columns}
          getRowId={(row) => row.spec_id}
          paginationModel={{ page: 0, pageSize: 25 }}
          rowCount={rows.length}
          rows={rows}
          {...tourAnchor(TOUR_ANCHORS.builderSpecsCatalog)}
        />
      </QueryState>
      <UploadSpecDialog onClose={() => setUploadOpen(false)} open={uploadOpen} />
    </Stack>
  )
}

import DownloadIcon from '@mui/icons-material/Download'
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Typography,
} from '@mui/material'
import { useMemo, useState } from 'react'

import { buildExportSnapshot, formatExportSnapshot } from '../lib/exportSnapshot'
import { JsonBlock } from './JsonBlock'
import { SensitiveDataNotice } from './SensitiveDataNotice'

type ExportSnapshotDialogProps = {
  data: unknown
  filters?: Record<string, unknown>
  open: boolean
  route: string
  selectedContext?: unknown
  title: string
  onClose: () => void
}

export function ExportSnapshotDialog({
  data,
  filters,
  onClose,
  open,
  route,
  selectedContext,
  title,
}: ExportSnapshotDialogProps) {
  const [includeBodies, setIncludeBodies] = useState(false)
  const [confirmedIncludeBodies, setConfirmedIncludeBodies] = useState(false)
  const snapshot = useMemo(
    () => buildExportSnapshot({ data, filters, includeBodies, route, selectedContext, title }),
    [data, filters, includeBodies, route, selectedContext, title],
  )
  const preview = formatExportSnapshot(snapshot)
  const downloadDisabled = includeBodies && !confirmedIncludeBodies

  function handleDownload() {
    if (downloadDisabled) return

    const blob = new Blob([preview], { type: 'application/json' })
    const href = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = href
    anchor.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'apipilot'}-snapshot.json`
    anchor.click()
    URL.revokeObjectURL(href)
  }

  function handleClose() {
    setIncludeBodies(false)
    setConfirmedIncludeBodies(false)
    onClose()
  }

  return (
    <Dialog fullWidth maxWidth="md" onClose={handleClose} open={open}>
      <DialogTitle>Export snapshot</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography color="text.secondary" variant="body2">
            Export current visible sanitized data, selected context, and route filters. Body fields are excluded unless explicitly enabled.
          </Typography>
          <FormControlLabel
            control={
              <Checkbox
                checked={includeBodies}
                onChange={(event) => {
                  setIncludeBodies(event.target.checked)
                  setConfirmedIncludeBodies(false)
                }}
              />
            }
            label="Include visible bodies"
          />
          {includeBodies ? (
            <>
              <SensitiveDataNotice>
                Visible bodies are sanitized by the backend where supported, but exports can still contain sensitive payload context. Confirm before downloading.
              </SensitiveDataNotice>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={confirmedIncludeBodies}
                    onChange={(event) => setConfirmedIncludeBodies(event.target.checked)}
                  />
                }
                label="I reviewed the risk and want to include visible bodies"
              />
            </>
          ) : null}
          <JsonBlock ariaLabel="export preview" maxHeight={360} value={preview} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
        <Button disabled={downloadDisabled} onClick={handleDownload} startIcon={<DownloadIcon />} variant="contained">
          Download JSON
        </Button>
      </DialogActions>
    </Dialog>
  )
}

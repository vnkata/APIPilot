import {
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from '@mui/material'

import { encodeRoutePart, formatBytes, formatDateTime } from '../../shared/lib/format'
import { AppLink } from '../../shared/ui/AppLink'
import { EmptyState } from '../../shared/ui/EmptyState'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import { useRuns } from './api'

export function RunsPage() {
  const runsQuery = useRuns()
  const runs = runsQuery.data?.runs ?? []

  return (
    <Stack spacing={2}>
      <PageHeader
        eyebrow="APIPilot artifact backend"
        title="Runs"
        subtitle="Read-only local cache catalog. Select a run to inspect operations, graphs, constraints, artifacts, reports, test cases, and HAR history."
        {...tourAnchor(TOUR_ANCHORS.runsHeader)}
      />

      <QueryState
        empty={runs.length === 0}
        emptyDescription="No APIPilot cache runs were found at the backend cache root."
        emptyTitle="No runs available"
        error={runsQuery.error}
        isError={runsQuery.isError}
        isLoading={runsQuery.isLoading}
        onRetry={() => void runsQuery.refetch()}
      >
        {runs.length === 0 ? (
          <EmptyState title="No runs available" />
        ) : (
          <Grid container spacing={2} {...tourAnchor(TOUR_ANCHORS.runsCatalog)}>
            {runs.map((run) => {
              const href = `/runs/${encodeRoutePart(run.run_name)}`
              return (
                <Grid key={run.run_name} size={{ xs: 12, md: 6, xl: 4 }}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardActionArea component="div" sx={{ height: '100%' }}>
                      <CardContent>
                        <Stack spacing={1.5}>
                          <Stack direction="row" spacing={2} sx={{ justifyContent: 'space-between' }}>
                            <Typography component="h2" variant="h3">
                              <AppLink href={href}>{run.run_name}</AppLink>
                            </Typography>
                            <Chip
                              color={run.has_history ? 'success' : 'default'}
                              label={run.has_history ? 'history' : 'no history'}
                              size="small"
                            />
                          </Stack>
                          <Typography color="text.secondary" variant="body2">
                            {run.artifact_count} artifacts · {formatBytes(run.size_bytes)}
                          </Typography>
                          <Typography color="text.secondary" variant="caption">
                            Modified {formatDateTime(run.modified_at)}
                          </Typography>
                        </Stack>
                      </CardContent>
                    </CardActionArea>
                  </Card>
                </Grid>
              )
            })}
          </Grid>
        )}
      </QueryState>
    </Stack>
  )
}

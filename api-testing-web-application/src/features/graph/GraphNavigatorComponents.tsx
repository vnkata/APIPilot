import {
  Box,
  Chip,
  Stack,
  Typography,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
  type NodeProps,
} from 'reactflow'

import type { NavigatorEdgeData, NavigatorNodeData } from './graphViewModels'

const riskColor: Record<NavigatorNodeData['risk'], string> = {
  danger: 'error.main',
  neutral: 'text.secondary',
  success: 'success.main',
  warning: 'warning.main',
}

export function OperationGraphNode({ data }: NodeProps<NavigatorNodeData>) {
  return (
    <Box
      sx={{
        bgcolor: 'background.paper',
        border: '1px solid',
        borderColor: data.isSelected ? 'primary.main' : riskColor[data.risk],
        borderRadius: 1,
        boxShadow: data.isSelected ? 4 : data.isPathNode ? 2 : 0,
        minWidth: 210,
        p: 1,
      }}
    >
      <Stack spacing={0.75}>
        <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
          <Chip
            color={data.risk === 'danger' ? 'error' : data.risk === 'success' ? 'success' : 'default'}
            label={data.statusLabel}
            size="small"
            variant={data.risk === 'neutral' ? 'outlined' : 'filled'}
          />
          {data.isPathNode ? <Chip label="Path" size="small" variant="outlined" /> : null}
        </Stack>
        <Typography sx={{ fontWeight: 800, lineHeight: 1.2, overflowWrap: 'anywhere' }} variant="body2">
          {data.label}
        </Typography>
        <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="caption">
          {data.operationId}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {data.degreeLabel}
        </Typography>
      </Stack>
    </Box>
  )
}

export function EvidenceGraphEdge({
  data,
  id,
  markerEnd,
  sourcePosition,
  sourceX,
  sourceY,
  targetPosition,
  targetX,
  targetY,
}: EdgeProps<NavigatorEdgeData>) {
  const theme = useTheme()
  const [edgePath, labelX, labelY] = getBezierPath({
    sourcePosition,
    sourceX,
    sourceY,
    targetPosition,
    targetX,
    targetY,
  })

  return (
    <>
      <BaseEdge
        id={id}
        markerEnd={markerEnd}
        path={edgePath}
        style={{
          stroke: data?.isPathEdge ? theme.palette.primary.main : theme.palette.text.secondary,
          strokeWidth: data?.isPathEdge ? 2.4 : 1.4,
        }}
      />
      <EdgeLabelRenderer>
        <Box
          sx={{
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: data?.isPathEdge ? 'primary.main' : 'divider',
            borderRadius: 1,
            fontSize: 11,
            fontWeight: 800,
            px: 0.75,
            py: 0.25,
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            position: 'absolute',
            pointerEvents: 'all',
          }}
        >
          {data?.evidenceCount ?? 0} evidence
        </Box>
      </EdgeLabelRenderer>
    </>
  )
}

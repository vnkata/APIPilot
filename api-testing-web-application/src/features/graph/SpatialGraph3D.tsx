import { Box, Stack, Typography } from '@mui/material'
import ForceGraph3D from 'react-force-graph-3d'

import type { SpatialGraphData } from './graphViewModels'

type SpatialGraph3DProps = {
  data: SpatialGraphData
  motionEnabled: boolean
  onNodeSelect: (operationId: string) => void
}

type SpatialNode = SpatialGraphData['nodes'][number]
type SpatialLink = SpatialGraphData['links'][number]

function linkEndpointId(endpoint: string | SpatialNode) {
  return typeof endpoint === 'string' ? endpoint : endpoint.id
}

export function SpatialGraph3D({ data, motionEnabled, onNodeSelect }: SpatialGraph3DProps) {
  return (
    <Stack spacing={1.5}>
      <Stack spacing={0.5}>
        <Typography component="h2" variant="h3">
          Spatial dependency graph
        </Typography>
        <Typography color="text.secondary" variant="body2">
          Experimental desktop 3D view. Use Journey or Navigator lists for keyboard-first review.
        </Typography>
      </Stack>
      <Box
        aria-label="Spatial graph viewport"
        role="region"
        sx={{
          bgcolor: '#020617',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          height: 520,
          overflow: 'hidden',
        }}
      >
        <ForceGraph3D
          backgroundColor="#020617"
          graphData={data}
          height={520}
          linkColor={(link) => (link as SpatialLink).color}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={(link) => (motionEnabled && (link as SpatialLink).isPathLink ? 3 : 0)}
          linkLabel={(link) => {
            const item = link as SpatialLink
            return `${linkEndpointId(item.source)} -> ${linkEndpointId(item.target)} (${item.status})`
          }}
          linkWidth={(link) => ((link as SpatialLink).isPathLink ? 2.2 : 1)}
          nodeAutoColorBy="group"
          nodeColor={(node) => (node as SpatialNode).color}
          nodeLabel={(node) => {
            const item = node as SpatialNode
            return `${item.name} (${item.risk})`
          }}
          nodeRelSize={5}
          nodeVal={(node) => (node as SpatialNode).val}
          onNodeClick={(node) => onNodeSelect((node as SpatialNode).id)}
        />
      </Box>
    </Stack>
  )
}

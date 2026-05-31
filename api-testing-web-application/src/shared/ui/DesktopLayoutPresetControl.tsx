import ViewColumnIcon from '@mui/icons-material/ViewColumn'
import {
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
} from '@mui/material'

import type { WorkspaceLayoutPreset } from '../lib/workspaceStorage'

type LayoutOption = {
  description: string
  label: string
  value: WorkspaceLayoutPreset
}

const layoutOptions: LayoutOption[] = [
  { description: 'Keep table, graph, and inspector balanced.', label: 'Balanced', value: 'balanced' },
  { description: 'Give operation tables more desktop width.', label: 'Table focus', value: 'table' },
  { description: 'Give graph evidence more desktop width.', label: 'Graph focus', value: 'graph' },
  { description: 'Give selected entity details more desktop width.', label: 'Inspector focus', value: 'inspector' },
]

type DesktopLayoutPresetControlProps = {
  onChange: (value: WorkspaceLayoutPreset) => void
  value: WorkspaceLayoutPreset
}

export function DesktopLayoutPresetControl({ onChange, value }: DesktopLayoutPresetControlProps) {
  return (
    <ToggleButtonGroup
      aria-label="Workspace layout preset"
      exclusive
      onChange={(_, nextValue: WorkspaceLayoutPreset | null) => {
        if (nextValue) onChange(nextValue)
      }}
      size="small"
      value={value}
    >
      {layoutOptions.map((option) => (
        <Tooltip key={option.value} title={option.description}>
          <ToggleButton aria-label={option.label} value={option.value}>
            {option.value === 'balanced' ? <ViewColumnIcon fontSize="small" /> : option.label}
          </ToggleButton>
        </Tooltip>
      ))}
    </ToggleButtonGroup>
  )
}

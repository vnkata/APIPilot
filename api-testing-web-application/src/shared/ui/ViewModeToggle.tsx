import { ToggleButton, ToggleButtonGroup, Tooltip } from '@mui/material'

export type ViewModeOption<TValue extends string> = {
  description?: string
  label: string
  value: TValue
}

type ViewModeToggleProps<TValue extends string> = {
  ariaLabel: string
  onChange: (value: TValue) => void
  options: Array<ViewModeOption<TValue>>
  value: TValue
}

export function ViewModeToggle<TValue extends string>({
  ariaLabel,
  onChange,
  options,
  value,
}: ViewModeToggleProps<TValue>) {
  return (
    <ToggleButtonGroup
      aria-label={ariaLabel}
      exclusive
      onChange={(_, nextValue: TValue | null) => {
        if (nextValue) onChange(nextValue)
      }}
      size="small"
      value={value}
    >
      {options.map((option) => {
        const button = (
          <ToggleButton key={option.value} value={option.value}>
            {option.label}
          </ToggleButton>
        )

        return option.description ? (
          <Tooltip describeChild key={option.value} title={option.description}>
            {button}
          </Tooltip>
        ) : (
          button
        )
      })}
    </ToggleButtonGroup>
  )
}

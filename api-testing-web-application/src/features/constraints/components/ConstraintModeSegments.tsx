import { replaceSearchParams } from '../../../shared/lib/navigation'
import { ViewModeToggle } from '../../../shared/ui/ViewModeToggle'
import type { ConstraintTab } from '../ConstraintsPage'

export type ConstraintMode = 'dynamic' | 'explorer' | 'invariants' | 'static' | 'workbench'

type ConstraintModeSegmentsProps = {
  constraintTab: ConstraintTab
  constraintsView: 'matrix' | 'table' | 'workbench'
}

function selectedMode(constraintsView: ConstraintModeSegmentsProps['constraintsView'], constraintTab: ConstraintTab): ConstraintMode {
  if (constraintsView === 'workbench' || constraintsView === 'matrix') return 'workbench'
  return constraintTab
}

export function ConstraintModeSegments({ constraintTab, constraintsView }: ConstraintModeSegmentsProps) {
  return (
    <ViewModeToggle
      ariaLabel="Constraint workspace mode"
      onChange={(value) => {
        if (value === 'workbench') {
          replaceSearchParams({
            constraintId: undefined,
            constraintTab: 'explorer',
            constraintsView: 'workbench',
            invariantId: undefined,
            offset: 0,
          })
          return
        }

        replaceSearchParams({
          constraintId: undefined,
          constraintTab: value,
          constraintsView: 'table',
          invariantId: undefined,
          offset: 0,
        })
      }}
      options={[
        { description: 'Readable constraint triage workspace.', label: 'Workbench', value: 'workbench' },
        { description: 'Advanced unified constraint table.', label: 'Explorer', value: 'explorer' },
        { description: 'Static constraint debug table.', label: 'Static', value: 'static' },
        { description: 'Dynamic constraint debug table.', label: 'Dynamic', value: 'dynamic' },
        { description: 'Invariant debug table.', label: 'Invariants', value: 'invariants' },
      ]}
      value={selectedMode(constraintsView, constraintTab)}
    />
  )
}

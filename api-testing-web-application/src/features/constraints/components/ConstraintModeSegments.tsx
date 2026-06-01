import { replaceSearchParams } from '../../../shared/lib/navigation'
import { ViewModeToggle } from '../../../shared/ui/ViewModeToggle'
import type { ConstraintTab } from '../ConstraintsPage'

export type ConstraintMode = 'combination' | 'dynamic' | 'explorer' | 'invariants' | 'static' | 'workbench'

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
            combinationId: undefined,
            constraintTab: 'explorer',
            constraintsView: 'workbench',
            invariantId: undefined,
            offset: 0,
          })
          return
        }

        replaceSearchParams({
          combinationId: undefined,
          constraintId: undefined,
          constraintTab: value,
          constraintsView: 'table',
          invariantId: undefined,
          offset: 0,
        })
      }}
      options={[
        { description: 'Readable constraint triage workspace.', label: 'Workbench', value: 'workbench' },
        { description: 'Combined static/dynamic resolution evidence.', label: 'Combination', value: 'combination' },
        { description: 'Advanced unified constraint table.', label: 'Explorer', value: 'explorer' },
        { description: 'Static constraint debug table.', label: 'Static', value: 'static' },
        { description: 'Mapped dynamic constraints derived from Daikon invariants.', label: 'Dynamic', value: 'dynamic' },
        { description: 'Raw Daikon invariant rows behind dynamic constraints.', label: 'Raw invariants', value: 'invariants' },
      ]}
      value={selectedMode(constraintsView, constraintTab)}
    />
  )
}

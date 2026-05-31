import { useCallback } from 'react'

import { replaceSearchParams, type SearchParamValue } from './navigation'

type SearchUpdates = Record<string, SearchParamValue>

function useSearchActions() {
  return useCallback((updates: SearchUpdates) => {
    replaceSearchParams(updates)
  }, [])
}

export function useRunWorkspaceSearchActions() {
  const apply = useSearchActions()

  return {
    applySavedView(search: Record<string, SearchParamValue>, savedViewId?: string) {
      apply({ ...search, savedViewId })
    },
    selectEdge(edgeId: string | undefined) {
      apply({ edgeId, operationId: undefined, operationKey: undefined, sequenceId: undefined })
    },
    selectOperation(operationKey: string | undefined, operationId?: string) {
      apply({ edgeId: undefined, operationId, operationKey, sequenceId: undefined })
    },
    selectSequence(sequenceId: string | undefined) {
      apply({ edgeId: undefined, operationId: undefined, operationKey: undefined, sequenceId })
    },
    setQuery(q: string) {
      apply({ offset: 0, q })
    },
    setWorkspaceView(workspaceView: string) {
      apply({ workspaceView })
    },
  }
}

export function useOperationsSearchActions() {
  const apply = useSearchActions()

  return {
    apply,
    selectOperation(operationKey: string | undefined) {
      apply({ operationKey })
    },
    setQuery(q: string) {
      apply({ offset: 0, q })
    },
  }
}

export function useGraphSearchActions() {
  const apply = useSearchActions()

  return {
    apply,
    selectEdge(edgeId: string | undefined) {
      apply({ edgeId })
    },
    selectOperation(operationId: string | undefined) {
      apply({ operationId })
    },
    selectSequence(sequenceId: string | undefined) {
      apply({ sequenceId })
    },
  }
}

import { useEffect, useState } from 'react'

import type { TourAnchorId } from './productTourTypes'

export type TourTargetState = {
  element: HTMLElement | null
  rect: DOMRect | null
  status: 'found' | 'missing'
}

const missingTourTargetState: TourTargetState = {
  element: null,
  rect: null,
  status: 'missing',
}

function findTourTarget(anchorId: TourAnchorId) {
  return document.querySelector<HTMLElement>(`[data-tour-anchor="${anchorId}"]`)
}

function prefersReducedMotion() {
  if (typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useTourTargetRect(anchorId: TourAnchorId | undefined, active: boolean): TourTargetState {
  const [targetState, setTargetState] = useState<TourTargetState>(missingTourTargetState)
  const isTracking = Boolean(active && anchorId)

  useEffect(() => {
    if (!isTracking || !anchorId) return undefined
    const resolvedAnchorId = anchorId

    let frame = 0
    let disposed = false

    function updateTarget(scrollIntoView = false) {
      if (disposed) return
      if (frame) window.cancelAnimationFrame(frame)
      const element = findTourTarget(resolvedAnchorId)
      if (!element) {
        frame = window.requestAnimationFrame(() => {
          setTargetState(missingTourTargetState)
        })
        return
      }

      if (scrollIntoView && typeof element.scrollIntoView === 'function') {
        element.scrollIntoView({
          behavior: prefersReducedMotion() ? 'auto' : 'smooth',
          block: 'center',
          inline: 'nearest',
        })
      }

      frame = window.requestAnimationFrame(() => {
        setTargetState({
          element,
          rect: element.getBoundingClientRect(),
          status: 'found',
        })
      })
    }

    updateTarget(true)

    const handleUpdate = () => updateTarget(false)
    window.addEventListener('resize', handleUpdate)
    window.addEventListener('scroll', handleUpdate, true)

    return () => {
      disposed = true
      window.cancelAnimationFrame(frame)
      window.removeEventListener('resize', handleUpdate)
      window.removeEventListener('scroll', handleUpdate, true)
    }
  }, [anchorId, isTracking])

  return isTracking ? targetState : missingTourTargetState
}

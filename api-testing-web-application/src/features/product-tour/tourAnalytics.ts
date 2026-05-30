import type { TourAnalyticsEvent } from './productTourTypes'

export type TourEventEmitter = (event: TourAnalyticsEvent) => void

let tourEventEmitter: TourEventEmitter = () => undefined

export function emitTourEvent(event: TourAnalyticsEvent) {
  tourEventEmitter(event)
}

export function setTourEventEmitter(emitter: TourEventEmitter) {
  tourEventEmitter = emitter

  return () => {
    if (tourEventEmitter === emitter) {
      tourEventEmitter = () => undefined
    }
  }
}

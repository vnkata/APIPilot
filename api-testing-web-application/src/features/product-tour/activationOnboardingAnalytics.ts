import type { ActivationOnboardingEvent } from './activationOnboardingTypes'

export type ActivationOnboardingEventEmitter = (event: ActivationOnboardingEvent) => void

let activationOnboardingEventEmitter: ActivationOnboardingEventEmitter = () => undefined

export function emitActivationOnboardingEvent(event: ActivationOnboardingEvent) {
  activationOnboardingEventEmitter(event)
}

export function setActivationOnboardingEventEmitter(emitter: ActivationOnboardingEventEmitter) {
  activationOnboardingEventEmitter = emitter

  return () => {
    if (activationOnboardingEventEmitter === emitter) {
      activationOnboardingEventEmitter = () => undefined
    }
  }
}

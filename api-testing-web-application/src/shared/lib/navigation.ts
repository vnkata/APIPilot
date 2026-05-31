export type SearchParamValue = boolean | number | string | null | undefined

type NavigationAdapter = {
  navigateInApp: (path: string) => void
  replaceSearchParams: (updates: Record<string, SearchParamValue>) => void
}

let navigationAdapter: NavigationAdapter | undefined

export function setNavigationAdapter(adapter: NavigationAdapter) {
  navigationAdapter = adapter
}

export function resetNavigationAdapter() {
  navigationAdapter = undefined
}

export function applySearchParamUpdates(
  currentSearch: Record<string, unknown>,
  updates: Record<string, SearchParamValue>,
) {
  const nextSearch: Record<string, unknown> = { ...currentSearch }

  Object.entries(updates).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === false) {
      delete nextSearch[key]
      return
    }

    nextSearch[key] = value
  })

  return nextSearch
}

export function navigateInApp(path: string) {
  navigationAdapter?.navigateInApp(path)
}

export function replaceSearchParams(updates: Record<string, SearchParamValue>) {
  navigationAdapter?.replaceSearchParams(updates)
}

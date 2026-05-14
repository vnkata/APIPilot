export function navigateInApp(path: string) {
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

type SearchParamValue = boolean | number | string | null | undefined

export function replaceSearchParams(updates: Record<string, SearchParamValue>) {
  const url = new URL(window.location.href)

  Object.entries(updates).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === false) {
      url.searchParams.delete(key)
      return
    }

    url.searchParams.set(key, String(value))
  })

  window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

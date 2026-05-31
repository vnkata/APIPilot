import { CssBaseline } from '@mui/material'
import { ThemeProvider } from '@mui/material/styles'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'
import type { PropsWithChildren, ReactElement } from 'react'
import { Provider as ReduxProvider } from 'react-redux'

import { createAppStore, type AppStore } from '../app/store'
import {
  applySearchParamUpdates,
  setNavigationAdapter,
  type SearchParamValue,
} from '../shared/lib/navigation'
import { createAppTheme } from '../theme'

type RenderWithProvidersOptions = RenderOptions & {
  store?: AppStore
  queryClient?: QueryClient
}

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
}

export function renderWithProviders(
  ui: ReactElement,
  {
    store = createAppStore(),
    queryClient = createTestQueryClient(),
    ...renderOptions
  }: RenderWithProvidersOptions = {},
) {
  setNavigationAdapter({
    navigateInApp: (path) => {
      window.history.pushState({}, '', path)
      window.dispatchEvent(new PopStateEvent('popstate'))
    },
    replaceSearchParams: (updates: Record<string, SearchParamValue>) => {
      const currentSearch = Object.fromEntries(new URLSearchParams(window.location.search))
      const nextSearch = applySearchParamUpdates(currentSearch, updates)
      const searchParams = new URLSearchParams()

      Object.entries(nextSearch).forEach(([key, value]) => {
        searchParams.set(key, String(value))
      })

      window.history.replaceState(
        {},
        '',
        `${window.location.pathname}${searchParams.size ? `?${searchParams}` : ''}${window.location.hash}`,
      )
      window.dispatchEvent(new PopStateEvent('popstate'))
    },
  })

  function Wrapper({ children }: PropsWithChildren) {
    return (
      <ReduxProvider store={store}>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider theme={createAppTheme(store.getState().workspacePreferences.themeMode)}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </QueryClientProvider>
      </ReduxProvider>
    )
  }

  return {
    store,
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}

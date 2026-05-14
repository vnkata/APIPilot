import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'
import type { PropsWithChildren, ReactElement } from 'react'
import { Provider as ReduxProvider } from 'react-redux'

import { createAppStore, type AppStore } from '../app/store'

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
  function Wrapper({ children }: PropsWithChildren) {
    return (
      <ReduxProvider store={store}>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </ReduxProvider>
    )
  }

  return {
    store,
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}

import type { PropsWithChildren } from 'react'
import { useMemo } from 'react'
import { CssBaseline } from '@mui/material'
import { ThemeProvider } from '@mui/material/styles'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Provider as ReduxProvider } from 'react-redux'

import { selectThemeMode } from '../features/workspace-preferences/workspacePreferencesSlice'
import { useAppSelector } from './hooks'
import { queryClient } from './queryClient'
import { store } from './store'
import { createAppTheme } from './theme'

function ThemedWorkspace({ children }: PropsWithChildren) {
  const themeMode = useAppSelector(selectThemeMode)
  const theme = useMemo(() => createAppTheme(themeMode), [themeMode])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  )
}

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ReduxProvider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemedWorkspace>{children}</ThemedWorkspace>
        {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
      </QueryClientProvider>
    </ReduxProvider>
  )
}

import { RouterProvider } from '@tanstack/react-router'
import { lazy, Suspense } from 'react'

import { router } from './app/router'

const TanStackRouterDevtools = lazy(async () => {
  const module = await import('@tanstack/router-devtools')
  return { default: module.TanStackRouterDevtools }
})

export default function App() {
  const devtoolsEnabled = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEVTOOLS !== 'false'

  return (
    <>
      <RouterProvider router={router} />
      {devtoolsEnabled ? (
        <Suspense fallback={null}>
          <TanStackRouterDevtools router={router} />
        </Suspense>
      ) : null}
    </>
  )
}

import { lazy, Suspense, type ReactNode } from 'react'
import {
  createRootRoute,
  createRoute,
  createRouter,
  Navigate,
  parseSearchWith,
  stringifySearchWith,
} from '@tanstack/react-router'

import { AppShell } from './AppShell'
import {
  artifactsSearchSchema,
  compareSearchSchema,
  constraintsSearchSchema,
  graphSearchSchema,
  historySearchSchema,
  operationsSearchSchema,
  reportsSearchSchema,
  runOverviewSearchSchema,
  testCasesSearchSchema,
} from './searchParams'
import { PageSkeleton } from '../shared/ui/PageSkeleton'
import { RunOverviewPage } from '../features/runs/RunOverviewPage'
import { RunsPage } from '../features/runs/RunsPage'

const LazyGraphPage = lazy(() =>
  import('../features/graph/GraphPage').then((module) => ({ default: module.GraphPage })),
)
const LazyOperationsPage = lazy(() =>
  import('../features/operations/OperationsPage').then((module) => ({ default: module.OperationsPage })),
)
const LazyConstraintsPage = lazy(() =>
  import('../features/constraints/ConstraintsPage').then((module) => ({ default: module.ConstraintsPage })),
)
const LazyArtifactsPage = lazy(() =>
  import('../features/artifacts/ArtifactsPage').then((module) => ({ default: module.ArtifactsPage })),
)
const LazyReportsPage = lazy(() =>
  import('../features/reports/ReportsPage').then((module) => ({ default: module.ReportsPage })),
)
const LazyTestCasesPage = lazy(() =>
  import('../features/test-cases/TestCasesPage').then((module) => ({ default: module.TestCasesPage })),
)
const LazyHistoryPage = lazy(() =>
  import('../features/history/HistoryPage').then((module) => ({ default: module.HistoryPage })),
)
const LazyComparePage = lazy(() =>
  import('../features/compare/ComparePage').then((module) => ({ default: module.ComparePage })),
)

function RouteFallback({ children }: { children: ReactNode }) {
  return <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
}

const rootRoute = createRootRoute({
  component: AppShell,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <Navigate to="/runs" replace />,
})

const runsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs',
  component: RunsPage,
})

const compareRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/compare',
  validateSearch: (search) => compareSearchSchema.parse(search),
  component: function CompareRoute() {
    const search = compareRoute.useSearch()
    return (
      <RouteFallback>
        <LazyComparePage search={search} />
      </RouteFallback>
    )
  },
})

const runOverviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName',
  validateSearch: (search) => runOverviewSearchSchema.parse(search),
  component: function RunOverviewRoute() {
    const { runName } = runOverviewRoute.useParams()
    const search = runOverviewRoute.useSearch()
    return <RunOverviewPage runName={runName} search={search} />
  },
})

const graphRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/graph',
  validateSearch: (search) => graphSearchSchema.parse(search),
  component: function GraphRoute() {
    const { runName } = graphRoute.useParams()
    const search = graphRoute.useSearch()
    return (
      <RouteFallback>
        <LazyGraphPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const operationsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/operations',
  validateSearch: (search) => operationsSearchSchema.parse(search),
  component: function OperationsRoute() {
    const { runName } = operationsRoute.useParams()
    const search = operationsRoute.useSearch()
    return (
      <RouteFallback>
        <LazyOperationsPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const constraintsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/constraints',
  validateSearch: (search) => constraintsSearchSchema.parse(search),
  component: function ConstraintsRoute() {
    const { runName } = constraintsRoute.useParams()
    const search = constraintsRoute.useSearch()
    return (
      <RouteFallback>
        <LazyConstraintsPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const artifactsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/artifacts',
  validateSearch: (search) => artifactsSearchSchema.parse(search),
  component: function ArtifactsRoute() {
    const { runName } = artifactsRoute.useParams()
    const search = artifactsRoute.useSearch()
    return (
      <RouteFallback>
        <LazyArtifactsPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const reportsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/reports',
  validateSearch: (search) => reportsSearchSchema.parse(search),
  component: function ReportsRoute() {
    const { runName } = reportsRoute.useParams()
    const search = reportsRoute.useSearch()
    return (
      <RouteFallback>
        <LazyReportsPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const testCasesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/test-cases',
  validateSearch: (search) => testCasesSearchSchema.parse(search),
  component: function TestCasesRoute() {
    const { runName } = testCasesRoute.useParams()
    const search = testCasesRoute.useSearch()
    return (
      <RouteFallback>
        <LazyTestCasesPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const historyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/runs/$runName/history',
  validateSearch: (search) => historySearchSchema.parse(search),
  component: function HistoryRoute() {
    const { runName } = historyRoute.useParams()
    const search = historyRoute.useSearch()
    return (
      <RouteFallback>
        <LazyHistoryPage runName={runName} search={search} />
      </RouteFallback>
    )
  },
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  runsRoute,
  compareRoute,
  runOverviewRoute,
  operationsRoute,
  graphRoute,
  constraintsRoute,
  artifactsRoute,
  reportsRoute,
  testCasesRoute,
  historyRoute,
])

export const router = createRouter({
  routeTree,
  parseSearch: parseSearchWith((value) => value),
  stringifySearch: stringifySearchWith(String),
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

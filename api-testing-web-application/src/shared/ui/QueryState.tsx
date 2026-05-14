import type { PropsWithChildren } from 'react'

import { ApiErrorAlert } from './ApiErrorAlert'
import { EmptyState } from './EmptyState'
import { PageSkeleton } from './PageSkeleton'

type QueryStateProps = PropsWithChildren<{
  empty?: boolean
  emptyDescription?: string
  emptyTitle?: string
  error: unknown
  isError: boolean
  isLoading: boolean
  onRetry?: () => void
}>

export function QueryState({
  children,
  empty = false,
  emptyDescription,
  emptyTitle = 'No data found',
  error,
  isError,
  isLoading,
  onRetry,
}: QueryStateProps) {
  if (isLoading) return <PageSkeleton />
  if (isError) return <ApiErrorAlert error={error} onRetry={onRetry} />
  if (empty) return <EmptyState title={emptyTitle} description={emptyDescription} />
  return <>{children}</>
}

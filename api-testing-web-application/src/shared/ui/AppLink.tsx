import MuiLink from '@mui/material/Link'
import type { MouseEvent, ReactNode } from 'react'

import { navigateInApp } from '../lib/navigation'

type AppLinkProps = {
  children: ReactNode
  href: string
  onNavigate?: () => void
}

export function AppLink({ children, href, onNavigate }: AppLinkProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return
    }

    event.preventDefault()
    navigateInApp(href)
    onNavigate?.()
  }

  return (
    <MuiLink href={href} onClick={handleClick} underline="hover">
      {children}
    </MuiLink>
  )
}

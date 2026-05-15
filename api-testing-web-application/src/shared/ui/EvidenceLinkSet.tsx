import { Stack } from '@mui/material'

import { AppLink } from './AppLink'

export type EvidenceLink = {
  href: string
  label: string
}

type EvidenceLinkSetProps = {
  links: EvidenceLink[]
}

export function EvidenceLinkSet({ links }: EvidenceLinkSetProps) {
  if (links.length === 0) return null

  return (
    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
      {links.map((link) => (
        <AppLink href={link.href} key={`${link.label}:${link.href}`}>
          {link.label}
        </AppLink>
      ))}
    </Stack>
  )
}

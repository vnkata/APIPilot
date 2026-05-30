import { Box } from '@mui/material'

import { monoFontFamily } from '../../theme/typography'
import { stringifySafe } from '../lib/json'

type JsonBlockProps = {
  ariaLabel?: string
  maxHeight?: number | string
  value: unknown
}

export function JsonBlock({ ariaLabel = 'JSON preview', maxHeight = 320, value }: JsonBlockProps) {
  return (
    <Box
      aria-label={ariaLabel}
      component="pre"
      sx={{
        bgcolor: (theme) => theme.apiTesting.code.background,
        border: '1px solid',
        borderColor: (theme) => theme.apiTesting.code.border,
        borderRadius: 1.25,
        color: (theme) => theme.apiTesting.code.text,
        fontFamily: monoFontFamily,
        fontSize: 12,
        lineHeight: 1.6,
        m: 0,
        maxHeight,
        overflow: 'auto',
        p: 2,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}
    >
      {stringifySafe(value)}
    </Box>
  )
}

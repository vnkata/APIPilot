import { Box } from '@mui/material'

type SpotlightFrameProps = {
  rect: DOMRect | null
}

export function SpotlightFrame({ rect }: SpotlightFrameProps) {
  if (!rect) return null

  const padding = 8

  return (
    <Box
      aria-hidden
      sx={(theme) => ({
        border: '2px solid',
        borderColor: theme.apiTesting.focus.outline,
        borderRadius: 1.5,
        boxShadow: `0 0 0 9999px rgba(2, 6, 23, 0.62), ${theme.apiTesting.focus.shadow}`,
        height: Math.max(rect.height + padding * 2, 40),
        left: Math.max(rect.left - padding, 8),
        pointerEvents: 'none',
        position: 'fixed',
        top: Math.max(rect.top - padding, 8),
        transition: theme.apiTesting.motion.transition.drawer,
        width: Math.max(rect.width + padding * 2, 40),
        zIndex: theme.zIndex.modal,
        '@media (prefers-reduced-motion: reduce)': {
          transition: 'none',
        },
      })}
    />
  )
}

export const uiFontFamily = [
  'Inter',
  'ui-sans-serif',
  'system-ui',
  '-apple-system',
  'BlinkMacSystemFont',
  '"Segoe UI"',
  'sans-serif',
].join(', ')

export const monoFontFamily = [
  '"JetBrains Mono"',
  '"SFMono-Regular"',
  'Consolas',
  '"Liberation Mono"',
  'Menlo',
  'monospace',
].join(', ')

export const typography = {
  allVariants: {
    letterSpacing: 0,
  },
  body1: { fontSize: '0.875rem', lineHeight: 1.58 },
  body2: { fontSize: '0.8125rem', lineHeight: 1.54 },
  button: {
    fontSize: '0.8125rem',
    fontWeight: 700,
    letterSpacing: 0,
    textTransform: 'none',
  },
  caption: { fontSize: '0.75rem', lineHeight: 1.35 },
  fontFamily: uiFontFamily,
  h1: { fontSize: '1.75rem', fontWeight: 800, letterSpacing: 0, lineHeight: 1.22 },
  h2: { fontSize: '1.35rem', fontWeight: 800, letterSpacing: 0, lineHeight: 1.25 },
  h3: { fontSize: '1rem', fontWeight: 750, letterSpacing: 0, lineHeight: 1.35 },
  overline: {
    fontSize: '0.6875rem',
    fontWeight: 800,
    letterSpacing: 0,
    lineHeight: 1.45,
    textTransform: 'uppercase',
  },
  subtitle1: { fontSize: '1rem', fontWeight: 700, lineHeight: 1.5 },
  subtitle2: { fontSize: '0.875rem', fontWeight: 750, lineHeight: 1.45 },
}

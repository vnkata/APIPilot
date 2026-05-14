declare module 'jest-axe' {
  export function axe(html: Document | Element | string): Promise<unknown>
  export const toHaveNoViolations: unknown
}

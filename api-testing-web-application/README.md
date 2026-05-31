# APIPilot Artifact Command Center

React/Vite frontend for inspecting APIPilot backend artifacts through the read-only FastAPI artifact API.

## Stack

- React 19, TypeScript, Vite
- MUI, TanStack Query, TanStack Router, Redux Toolkit
- Orval-generated API client under `src/shared/api/generated/`
- Vitest, Testing Library, MSW, Playwright, Storybook

## Development

```bash
npm install --legacy-peer-deps
npm run dev
```

The frontend defaults to `http://localhost:8000`. Override it with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Optional runtime env:

- `VITE_API_BASE_URL`: backend artifact API base URL.
- `VITE_API_TIMEOUT_MS`: Axios request timeout, default `15000`.
- `VITE_ENABLE_DEVTOOLS=false`: disable TanStack devtools in local-like builds.

## Validation

```bash
npm run lint
npm run typecheck
npm run test:run
npm run test:coverage
npm run build
npm run check
```

E2E uses a reproducible Python fixture backend backed by generated temporary artifacts:

```bash
npm run test:e2e
```

Visual desktop screenshot smoke is intentionally separate from `npm run check`:

```bash
npm run test:visual
```

Storybook uses MSW handlers from `src/test/msw/handlers.ts`:

```bash
npm run storybook
npm run build-storybook
```

Bundle analysis writes `dist/bundle-stats.html`:

```bash
npm run analyze
```

## Architecture Notes

- `src/app/`: providers, router, shell, Redux store.
- `src/features/`: run, operation, graph, constraint, artifact, report, test-case, history, compare, and command-palette workflows.
- `src/shared/`: generated API client, API/error helpers, config, reusable UI, formatting, navigation adapter.
- URL/search state is routed through TanStack Router navigation. Unit tests install a jsdom-only navigation adapter for page-level URL assertions.
- Server state belongs in TanStack Query. Redux is limited to workspace preferences and product-tour state.
- The backend HTTP contract is the boundary. The frontend must not read `.cache` directly.

## Bundle Expectations

Non-graph routes should not eagerly load graph, 3D, or editor surfaces. Graph and artifact routes intentionally lazy-load heavy areas:

- `SpatialGraph3D` is a documented large 3D chunk and should load only for Spatial graph mode.
- Monaco editor/diff viewer is lazy-loaded by artifact raw/compare views.
- DataGrid-heavy route panels are route-level chunks.

Use `npm run analyze` after dependency or routing changes.

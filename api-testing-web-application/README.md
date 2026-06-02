# APIPilot Artifact Command Center

React/Vite frontend for inspecting APIPilot artifacts and launching local APIPilot write-flow runs through the FastAPI backend.

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
npm run test:visual -- --update-snapshots
```

The checked visual baselines target 1440px desktop pages, including Builder pages after their UI stabilizes. The 1280px smoke captures remain output artifacts only until the layout is stable enough for CI gating.

Storybook uses MSW handlers from `src/test/msw/handlers.ts`:

```bash
npm run storybook
npm run build-storybook
```

Bundle analysis writes `dist/bundle-stats.html`:

```bash
npm run analyze
```

Regenerate the typed API client only after the backend OpenAPI contract changes:

```bash
npm run openapi:fetch
npm run api:generate
```

Never hand-edit files under `src/shared/api/generated/`.

## Architecture Notes

- `src/app/`: providers, router, shell, Redux store.
- `src/features/`: builder, run, workspace, operation, graph, constraint, artifact, report, test-case, history, compare, and command-palette workflows.
- `src/shared/`: generated API client, API/error helpers, config, reusable UI, formatting, navigation adapter.
- URL/search state is routed through TanStack Router navigation. Unit tests install a jsdom-only navigation adapter for page-level URL assertions.
- Server state belongs in TanStack Query. Redux is limited to workspace preferences and product-tour state.
- The backend HTTP contract is the boundary. The frontend must not read `.cache` directly.

## Builder Workflow

Use `/builder/specs` to upload OpenAPI JSON/YAML content, preview parsed operations, create a run configuration, and start a deterministic `dry_run` execution. Builder pages keep a mode-aware shell context so spec management, config building, and execution tracking stay visually separate from run investigation.

Builder routes:

- `/builder/specs`
- `/builder/specs/:specId`
- `/builder/run-configs/new?specId=...`
- `/builder/executions`
- `/builder/executions/:executionId`

Run Config Builder uses backend validation before create. The wizard includes a desktop summary strip for mode, validation, budget, and selected spec, plus sticky action buttons for validation/create/run. Live mode is visible but guarded by explicit confirmation because it can send requests to a configured target API.

Execution Detail polls active executions and event history until the execution reaches `completed`, `failed`, or `cancelled`. When a completed execution publishes a `run_name`, use the Open generated run action to inspect it in the existing run workspace.

### Builder Privacy

Run config drafts are browser-local under `apipilot.runConfigDrafts.v1`. Only non-sensitive fields are saved:

- spec id
- config name
- numeric settings
- booleans
- provider/model labels

The draft intentionally does not persist base URLs, headers, secret ref names, custom provider endpoints, validation responses, raw tokens, or resolved secrets.

Headers such as `Authorization`, `Cookie`, and `X-API-Key` default to env refs. Secret values should stay in environment variables configured outside the frontend.

## Desktop Investigation Workflow

- Open `/runs/:runName/workspace` from the sidebar after Overview.
- Use Workspace to filter operations, switch desktop layout presets, inspect graph evidence, keep the inspector open, pin evidence, and save URL-backed views.
- Saved Views, bookmarks, notes, layout presets, recent entities, and table column layouts are browser-local and versioned with these keys:
  - `apipilot.savedViews.v1`
  - `apipilot.bookmarks.v1`
  - `apipilot.workspaceNotes.v1`
  - `apipilot.tableLayouts.v1`
  - `apipilot.layoutPresets.v1`
  - `apipilot.recentEntities.v1`
  - `apipilot.tablePowerPresets.v1`
- Local notes/bookmarks are never sent to the backend. Export includes them only when the user explicitly selects the local-context checkbox.
- Export snapshots omit body-like fields by default and redact sensitive field names such as token, authorization, cookie, password, secret, api key, and session.
- Table Power bars expose column presets, current density, and copy-on-double-click behavior without adding a second table abstraction.
- Command Palette remains client-only and indexes navigation, current-run actions, Builder entries, saved views, bookmarks, recent entities, and current-run Compare shortcuts.

## Guided UX And Onboarding

APIPilot includes native, frontend-only guidance built on the existing Redux product-tour state under `apipilot.productTour.v1`.

- First-time users see a non-blocking "New to APIPilot?" prompt on the run catalog after the catalog tour has already been handled.
- The prompt offers three paths: inspect an existing run, build a new run, or compare evidence.
- The Help button in the app shell lists every tour available for the current route.
- Dense pages can expose multiple route tours. Constraints currently has separate fundamentals, workbench, and explorer tours.
- Coach marks support bullets, domain-term explanations, and "Why this matters" guidance.
- In-page learning panels and tooltips explain domain vocabulary without changing backend contracts.

Guided UX should stay native to the app: use MUI, existing theme tokens, existing Redux tour persistence, and route-aware anchors from `src/features/product-tour/tourAnchors.ts`.

## Compare Lab

`/compare` uses existing artifact catalog/content endpoints only. It now shows:

- artifact presence and metadata deltas;
- JSON structural added/removed/changed paths for JSON-like content;
- lazy Monaco raw/text diff only when raw mode is requested.

## Bundle Expectations

Non-graph routes should not eagerly load graph, 3D, or editor surfaces. Graph and artifact routes intentionally lazy-load heavy areas:

- `SpatialGraph3D` is a documented large 3D chunk and should load only for Spatial graph mode.
- Monaco editor/diff viewer is lazy-loaded by artifact raw/compare views.
- DataGrid-heavy route panels are route-level chunks.

Use `npm run analyze` after dependency or routing changes.

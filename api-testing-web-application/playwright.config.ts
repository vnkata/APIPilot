import { defineConfig, devices } from '@playwright/test'

const backendPort = 8765
const frontendPort = 5174
const backendURL = `http://127.0.0.1:${backendPort}`
const frontendURL = `http://127.0.0.1:${frontendPort}`

export default defineConfig({
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  testDir: './e2e',
  timeout: 45_000,
  use: {
    baseURL: frontendURL,
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: '../.venv/bin/python e2e/backend_fixture_server.py',
      env: {
        APIPILOT_E2E_ALLOWED_ORIGIN: frontendURL,
        APIPILOT_E2E_BACKEND_PORT: String(backendPort),
      },
      reuseExistingServer: false,
      timeout: 30_000,
      url: `${backendURL}/health`,
    },
    {
      command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${frontendPort}`,
      env: {
        VITE_API_BASE_URL: backendURL,
        VITE_ENABLE_DEVTOOLS: 'false',
      },
      reuseExistingServer: false,
      timeout: 30_000,
      url: frontendURL,
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})

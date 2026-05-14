# APIPilot E2E Fixtures

Playwright starts `e2e/backend_fixture_server.py`, which builds a sanitized local
artifact cache from the repository's Python fixture generator at
`tests/backend_artifact_fixtures.py`.

Do not copy raw `.cache` output into this directory. Keep E2E fixtures small,
sanitized, and deterministic.

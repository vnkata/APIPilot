# Tests Agent Guidance

This directory contains active pytest tests for APIPilot.

## Read First

- `../AGENTS.md`
- `../docs/ai/validation-matrix.md`
- `../docs/ai/source-of-truth-and-artifact-policy.md`

## Test Boundaries

- Prefer deterministic tests with `tmp_path`, `monkeypatch`, mocks, and sanitized fixtures.
- Do not require live LLM calls, live remote APIs, mutable service state, or large `.cache` artifacts in unit tests.
- Use small curated fixtures for backend artifact behavior.
- Keep generated raw artifacts and sensitive payloads out of tests unless sanitized.

## Active Layout

- `backend/`: FastAPI backend, artifact API, write-flow, Combination/HITL, OpenAPI, repository, and service tests.
- `constraint/`: constraint combiner, conflict resolver, counter-example planner/experiment, and combine report tests.
- `generators/`: request/value generator tests.
- `models/`: model provider and LLM adapter tests.
- `config/`: configuration loader, wizard, and main debug-mode tests.
- `memory/`, `reports/`, `utils/`: focused core support tests.
- `fixtures/`: reusable sanitized artifact builders and test data helpers.
- `fakes/`: reusable deterministic fakes for external boundaries.

Use capability-oriented file names and shared fixtures/fakes when a helper is reused by more than one test module. Prefer `pytest-mock` (`mocker`) over new `unittest.mock.patch` usage in active tests.

## Legacy Area

`legacy/` is excluded from default pytest discovery by root `pytest.ini`. It contains retired or stale invariant-classifier coverage that imports modules no longer present in the active architecture. Restore or redesign the active module before moving any legacy test back into the active suite.

Use targeted checks from `docs/ai/validation-matrix.md` and report full active-suite status honestly when checked.

## Live Tests

Tests or scripts that require live LLMs, remote APIs, or classifier restoration should be explicit opt-in and should not be part of the default automated suite.

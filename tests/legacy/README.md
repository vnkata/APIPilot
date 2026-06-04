# Legacy Test Area

This directory contains tests that are intentionally excluded from default
pytest discovery by the root `pytest.ini`.

The current legacy tests reference retired or missing invariant-classifier
modules such as `invariant_reader`, `classified_invariant_reader`, and
`invariant_classifier`. Keeping them here preserves the historical research
coverage without breaking active APIPilot collection.

To restore any test from this directory, first restore or redesign the active
module it imports, then move the focused coverage back under the relevant
capability directory in `tests/`.

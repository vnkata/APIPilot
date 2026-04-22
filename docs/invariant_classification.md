# Invariant Classification

Invariant Classification adds an LLM-backed review step after Daikon emits
`invariants.csv`. It keeps raw invariants immutable and writes a separate
`classified_invariants.csv` artifact.

For the end-to-end dynamic constraint mining flow, including `.decls`,
`.dtrace`, Daikon extraction, classification artifacts, Mermaid diagrams, and
Java extension porting notes, see
[`dynamic_constraint_mining.md`](dynamic_constraint_mining.md).

For a deeper explanation of spec excerpt budgets, selected schema paths, and
deterministic evidence checks, see
[`invariant_classifier_internals.md`](invariant_classifier_internals.md).

## Flow

```text
test_cases.decls + test_cases.dtrace
  -> InvariantExtractor
  -> invariants.csv
  -> InvariantClassifier
  -> classified_invariants.csv
```

The classifier builds a compact API spec excerpt, adds best-effort concrete
examples from cached test cases, and asks the configured LLM to classify each
invariant as:

- `true-positive`
- `false-positive`
- `inconclusive`

## Required Inputs

- A parsed `SpecificationParser` or compatible object exposing `operations`.
- A model object implementing `generate(...)` and `get_model_name()`.
- `cache_dir/invariants.csv`.
- Optional `cache_dir/test_cases.json` for concrete examples.

## Classify Existing Invariants

```python
from api_testing.constraint.dynamic_constraints.invariant_classifier import InvariantClassifier
from api_testing.dataset.specification_parser import SpecificationParser
from api_testing.models.llms.openai_model import OpenAIModel

spec = SpecificationParser(spec_path="datasets/Bills-api.json")
spec.parse_specification()

model = OpenAIModel(model="gpt-4.1-mini")
classifier = InvariantClassifier(
    spec_parser=spec,
    model=model,
    cache_dir=".cache/Bills API_3",
)

classified_path = classifier.classify_invariants(
    persist_debug_artifacts=True,
)
print(classified_path)
```

## Use DynamicConstraintMiner

Classify after `invariants.csv` already exists:

```python
from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner

miner = DynamicConstraintMiner(
    spec_parser=spec,
    model=model,
    cache_dir=".cache/Bills API_3",
)

classified_path = miner.classify_invariants(
    persist_debug_artifacts=True,
)
```

Run full dynamic mining and classification:

```python
artifacts = miner.mine_and_classify_dynamic_constraints(
    persist_debug_artifacts=True,
)

print(artifacts["decls_path"])
print(artifacts["dtrace_path"])
print(artifacts["invariants_path"])
print(artifacts["classified_invariants_path"])
```

`mine_dynamic_constraints()` is unchanged and still returns only the raw mining
artifacts.

## Output CSV

`classified_invariants.csv` uses the same `;` delimiter convention as
`invariants.csv`.

Columns:

- `pptname`
- `invariant`
- `invariantType`
- `variables`
- `postmanAssertion`
- `verdict`
- `confidence`
- `reason`
- `model`
- `promptVersion`
- `examplesCount`
- `approxNumberOfOperations`

Read it with:

```python
from api_testing.constraint.dynamic_constraints.classified_invariant_reader import (
    ClassifiedInvariantReader,
)

records = ClassifiedInvariantReader(cache_dir=".cache/Bills API_3").read_invariants()
```

## Debug Artifacts

When `persist_debug_artifacts=True`, JSON files are written under:

```text
cache_dir/classification_debug/0001.json
```

Debug payload fields:

- `record`: raw invariant row fields.
- `normalized_context`: parsed program point, variables, and invariant kind.
- `spec_excerpt`: compact request/response spec context sent to the prompt.
- `spec_excerpt_debug.shape`: excerpt budget shape, such as `simple_scalar`.
- `spec_excerpt_debug.budget_profile`: deterministic line budget used.
- `spec_excerpt_debug.matched_schema_paths`: schema entries actually rendered.
- `examples`: concrete examples recovered from cached test cases.
- `observed_evidence`: deterministic check showing whether recovered examples
  satisfy or contradict simple invariant operators.
- `spec_enum_evidence`: deterministic check for `one of` invariants against
  documented OpenAPI enums.
- `deterministic_correction`: present when the classifier corrected an LLM
  result that contradicted deterministic evidence.
- `result`: structured model result when classification succeeds.
- `error`: exception summary when the row falls back to `inconclusive`.

`matched_schema_paths` is intentionally compact. It contains selected paths,
not all candidates:

```json
[
  {
    "source": "response",
    "path": "items[].owner.name",
    "kind": "leaf",
    "match_score": 100
  }
]
```

## Local Examples

These module demos do not call an LLM by default:

```powershell
.venv/Scripts/python.exe -m api_testing.constraint.dynamic_constraints.classification.context_parser
.venv/Scripts/python.exe -m api_testing.constraint.dynamic_constraints.classification.spec_excerpt_builder
.venv/Scripts/python.exe -m api_testing.constraint.dynamic_constraints.invariant_classifier
```

## Tests

Classifier unit tests:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_invariant_classifier.py -q
```

Dynamic constraint miner integration tests:

```powershell
$env:RUN_DYNAMIC_CONSTRAINT_MINER = "1"
.venv/Scripts/python.exe -m pytest tests/test_dynamic_constraint_miner.py -q
```

Optional live OpenAI smoke test:

```powershell
$env:RUN_LIVE_INVARIANT_CLASSIFIER = "1"
$env:OPENAI_API_KEY = "<your key>"
.venv/Scripts/python.exe -m pytest tests/test_invariant_classifier.py -q
```

## Run Live Classifier Runner

For a practical live run across the current cached datasets, use the dedicated
runner:

```powershell
$env:OPENAI_API_KEY = "<your key>"
.venv/Scripts/python.exe scripts/run_invariant_classifier_live.py
```

The runner is intentionally simple and edit-friendly. To change the model,
output filename, target datasets, or per-cache limit, edit the constants near
the top of `scripts/run_invariant_classifier_live.py`.

Default behavior:

- Uses `OpenAIModel(model="gpt-4.1-mini")`.
- Processes the cache directories listed in `DATASET_TO_CACHE_DIR`.
- Reads each `cache_dir/invariants.csv`.
- Writes `cache_dir/classified_invariants.live.csv`.
- Enables `persist_debug_artifacts=True`, which writes debug JSON files under
  `cache_dir/classification_debug/`.
- Resumes from the live output CSV when `RESUME=True`.
- Uses limited worker-pool concurrency through `MAX_WORKERS`.
- Writes aggregate summaries:
  - `cache_dir/classified_invariants.live.summary.json`
  - `cache_dir/classified_invariants.live.summary.csv`

Warning: a full run performs one live LLM request per invariant row. This can
take substantial time and consume API credits. Set `LIMIT` in the script for a
small smoke run before running all invariants. If you use `LIMIT`, consider
temporarily changing `OUTPUT_FILENAME` as well so sample output is not confused
with a full live run.

The classifier also performs conservative local repair for common structured
output slips before validating with Pydantic. For example, `"confidence": "high"`
is coerced to `0.8`, numeric strings such as `"0.9"` are coerced to floats, and
fenced JSON is unwrapped. Ambiguous or invalid verdicts are still treated as
classification failures and become `inconclusive` rows.

For simple operators, the classifier also computes deterministic evidence checks
from recovered examples and documented enums. These checks prevent common live
LLM mistakes such as claiming `input.Take <= return.itemsPerPage` is contradicted
by a negative `Take`, or claiming a documented enum member is missing when the
excerpt contains it.

## Limitations

- Examples are best-effort and depend on cached test case payload quality.
- `approxNumberOfOperations` is local to the current `cache_dir`.
- Debug JSON is additive/internal; `classified_invariants.csv` is the stable
  contract.
- `matched_schema_paths` shows rendered excerpt paths only, not rejected
  candidates.

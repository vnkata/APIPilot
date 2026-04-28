# Invariant Classifier Internals

This document explains two components that are easy to underestimate when
reading the invariant classification flow:

- `SpecExcerptBuilder`: chooses the compact OpenAPI context sent to the LLM.
- `evidence_checker`: performs narrow deterministic checks over examples and
  documented enums before finalizing the classifier result.

Both components exist because LLM classification needs grounded context, but the
full OpenAPI spec and raw execution history are too large and noisy to paste
into every prompt.

## Where This Fits

```text
InvariantRecord
  -> InvariantContextParser
  -> SpecExcerptBuilder
  -> ExampleExtractor
  -> evidence_checker
  -> InvariantClassificationPrompt
  -> deterministic correction
  -> classified output + debug JSON
```

At a high level:

- `InvariantContextParser` turns a Daikon row into operation, variables, and
  program-point context.
- `SpecExcerptBuilder` selects the most relevant request/response schema lines.
- `ExampleExtractor` recovers concrete variable assignments from cached test
  cases.
- `evidence_checker` evaluates simple supported patterns against examples and
  OpenAPI enum declarations.
- The prompt asks the LLM for `true-positive`, `false-positive`, or
  `inconclusive`.
- The classifier can apply deterministic corrections when narrow evidence
  clearly contradicts the model output.

## SpecExcerptBuilder: What Problem It Solves

`SpecExcerptBuilder` answers this question:

> For this one invariant, which tiny slice of the OpenAPI operation should the
> LLM see?

It intentionally does not send the full spec. Full specs are often huge, include
many unrelated operations and fields, and increase cost/latency. More
importantly, irrelevant fields can distract the LLM and make it reason about the
wrong part of the API.

For each normalized invariant context, `build_with_debug()` returns:

| Field | Meaning |
| --- | --- |
| `excerpt` | Text sent to the prompt as the relevant API specification excerpt. |
| `shape` | The selected excerpt shape: `simple_scalar`, `nested_object`, `array_focused`, or `mixed_container_scalar`. |
| `budget_profile` | Deterministic caps that limit how many request/response/schema lines can be rendered. |
| `matched_schema_paths` | Debug metadata showing which request/response schema paths were actually rendered. |

The debug metadata is important: it lets you inspect whether the prompt saw the
field you expected. If the LLM says "field X is not defined", the first thing to
check is usually `classification_debug/<row>.json -> spec_excerpt` and
`spec_excerpt_debug.matched_schema_paths`.

## What Budget Means

In this codebase, a "budget" is not money or token accounting. It is a set of
deterministic caps over how much schema context the builder is allowed to render
for one invariant.

Current budget table from `SpecExcerptBuilder.DEFAULT_BUDGETS`:

| Shape | `max_request_lines` | `max_response_lines` | `max_container_fields` | `max_fallback_paths` |
| --- | ---: | ---: | ---: | ---: |
| `simple_scalar` | 1 | 1 | 0 | 3 |
| `nested_object` | 2 | 2 | 4 | 3 |
| `array_focused` | 2 | 2 | 4 | 3 |
| `mixed_container_scalar` | 2 | 3 | 3 | 3 |

Budget fields:

| Field | Purpose |
| --- | --- |
| `max_request_lines` | Maximum relevant request input lines to render. Required directly referenced request variables can raise the effective cap so they are not silently dropped. |
| `max_response_lines` | Maximum relevant response field/container lines to render. |
| `max_container_fields` | Maximum child fields shown when summarizing an object or array item container. |
| `max_fallback_paths` | Maximum nearby/available paths shown when the builder cannot directly match a variable. |

The shape is inferred from the invariant variables:

- `simple_scalar`: top-level scalar field, no array/nested container pressure.
- `nested_object`: nested object paths such as `return.owner.name`.
- `array_focused`: array or size expressions such as `size(return.items[])`.
- `mixed_container_scalar`: a mix of scalar fields plus nested/array context,
  such as `input.category == return.category` inside `items[]`.

## SpecExcerptBuilder Examples

The examples below use simplified snippets. Real excerpts also include the
endpoint and summary when available.

### Case 1: Simple Scalar Response Field

Invariant:

```text
return.totalResults >= 1
```

Shape:

```text
simple_scalar
```

Budget:

```json
{
  "max_request_lines": 1,
  "max_response_lines": 1,
  "max_container_fields": 0,
  "max_fallback_paths": 3
}
```

Typical excerpt:

```text
Endpoint: GET /widgets
Summary: List widgets
Relevant request inputs:
- This invariant does not reference request inputs.
Relevant response fields for status 200:
- response `totalResults`: integer; Total widgets
```

Why this is enough:

- The invariant only needs the type and basic meaning of `totalResults`.
- Adding unrelated fields like `items[]`, `pagination`, or `owner` would add
  noise without helping this invariant.

Without the budget, the prompt could include dozens of unrelated response
fields, making the LLM more likely to invent relationships or overfit to nearby
field names.

### Case 2: Request/Response Scalar Relationship

Invariant:

```text
input.category == return.category
```

Program point:

```text
get-/widgets&get-/widgets&200&items():::EXIT
```

This means `return.category` is interpreted relative to the response container
`items[]`.

Shape:

```text
mixed_container_scalar
```

Typical excerpt:

```text
Endpoint: GET /widgets
Summary: List widgets
Relevant request inputs:
- query parameter `category`: string; Widget category filter; enum=['books', 'games']
Relevant response fields for status 200:
- response `items[]`: array; Collection of widgets; items=object; item fields=category, id, owner
- response `items[].category`: string; enum=['books', 'games']
```

Why the budget matters:

- The request side must include `input.category`.
- The response side must include both the array container `items[]` and the leaf
  `items[].category`.
- The LLM needs the container line to understand that `return.category` means
  "category of each item", not a root-level response field.

Without this excerpt, the LLM may incorrectly say `return.category` is not
defined because it only sees root response fields.

### Case 3: Nested Response Object Field

Invariant:

```text
return.owner.name != ""
```

Program point:

```text
get-/widgets&get-/widgets&200&items():::EXIT
```

Shape:

```text
nested_object
```

Typical excerpt:

```text
Endpoint: GET /widgets
Summary: List widgets
Description: Returns widgets that match the provided filters.
Relevant request inputs:
- This invariant does not reference request inputs.
Relevant response fields for status 200:
- response `items[]`: array; Collection of widgets; items=object; item fields=category, id, owner, tags[]
- response `items[].owner`: object; Widget owner; fields=id, name, role; required=id, name
- response `items[].owner.name`: string; Owner display name
```

The selected schema paths might look like:

```json
[
  {"source": "response", "path": "items[]", "kind": "array_container", "match_score": 100},
  {"source": "response", "path": "items[].owner", "kind": "object_container", "match_score": 100},
  {"source": "response", "path": "items[].owner.name", "kind": "leaf", "match_score": 100}
]
```

Why this helps:

- The LLM sees the array container, object container, and leaf field.
- Required fields on `owner` can support the idea that `name` exists, but the
  LLM still has to decide whether non-empty string is guaranteed.

Without container-aware selection, the prompt may include only `owner.name`
without explaining where `owner` lives, or it may include the parent container
but omit the leaf field.

### Case 4: Response Array Size

Invariant:

```text
size(return.items[]) one of { 2 }
```

Shape:

```text
array_focused
```

Typical excerpt:

```text
Endpoint: GET /widgets
Summary: List widgets
Relevant request inputs:
- This invariant does not reference request inputs.
Relevant response fields for status 200:
- response `items[]`: array; Collection of widgets; items=object; item fields=category, id, owner, tags[]
```

Why this is the right slice:

- The invariant is about array size, so the array container matters more than
  individual item fields.
- If the spec does not include `minItems`, `maxItems`, or pagination semantics,
  the classifier should be cautious: observed size `2` alone is usually not
  enough to prove a stable API contract.

Without this context, the LLM might treat the observed size as a documented
contract and produce an overconfident `true-positive`.

### Case 5: Missing Request Variable

Invariant:

```text
input.assignee_username == input.iids[]
```

If the OpenAPI operation documents `assignee_username` but not `iids[]`, the
builder should not silently omit the missing variable. It should render the
matched input and report what could not be matched.

Typical excerpt:

```text
Endpoint: GET /issues
Relevant request inputs:
- query parameter `assignee_username`: string
- No direct request input match found for `iids[]`. Available parameters: assignee_username, iid, scope, state
Relevant response fields for status 200:
- This invariant does not reference response fields.
```

Why this matters:

- The LLM can distinguish "not documented" from "the builder forgot to include
  it."
- Debugging becomes much easier because the missing variable and available
  parameters are explicit.

Without this behavior, the prompt might only show `assignee_username`, causing
the LLM to correctly complain that `iids[]` is undefined, but without revealing
whether the omission came from the spec or from excerpt selection.

## What Breaks Without Budgeting

Without `SpecExcerptBuilder` budgets:

- Prompts become longer, slower, and more expensive.
- The LLM can anchor on unrelated request parameters or response fields.
- Nested fields can lose parent/container context.
- Array-size invariants can be evaluated without seeing array semantics.
- Request-only invariants can drop one side of the comparison.
- Debug artifacts would not show which schema paths were selected.
- Live runs would become harder to inspect because every prompt would contain a
  noisy, inconsistent amount of schema context.

The key point: the budget is a precision tool. It is small enough to keep the
prompt focused, but shape-aware enough to include containers when containers are
necessary for correct interpretation.

## evidence_checker: What Problem It Solves

`evidence_checker.py` answers two narrow deterministic questions:

1. Do recovered observed examples satisfy or contradict this simple invariant?
2. Does a `one of` invariant match, narrow, or conflict with a documented enum
   in the spec excerpt?

It is not a semantic classifier. It intentionally supports only a limited set of
patterns. Unsupported patterns return `not-evaluated` or `not-applicable`, and
the LLM remains responsible for judgment.

The classifier uses this evidence in two places:

- It passes evidence summaries into the prompt as additional grounding.
- It can apply deterministic corrections when evidence clearly contradicts the
  LLM output.

## ObservedEvidenceAnalysis

`analyze_observed_examples(invariant, examples)` returns
`ObservedEvidenceAnalysis`.

| Field | Meaning |
| --- | --- |
| `status` | `no-examples`, `not-evaluated`, or `evaluated`. |
| `kind` | Parsed expression kind, such as `one_of`, `substring`, or `comparison:<=`. |
| `support_count` | Number of evaluated examples that satisfy the invariant. |
| `contradiction_count` | Number of evaluated examples that contradict the invariant. |
| `unevaluated_count` | Number of examples that could not be evaluated. |
| `contradiction_examples` | Up to five concrete examples that contradict the invariant. |
| `summary` | Human-readable summary included in debug artifacts and prompt evidence. |

Supported observed patterns include:

- `x one of { ... }`
- `x is a substring of y`
- comparisons with `==`, `<=`, `>=`, `<`, `>`
- `LENGTH(x)` and `size(...)`-style values when examples provide matching
  assignments

Unsupported patterns are deliberate. For example, date predicates, URL
predicates, and complex sequence relationships should remain LLM-mediated until
there is a safe deterministic evaluator for them.

## Observed Evidence Examples

### Case 1: Supported Comparison With No Contradiction

Invariant:

```text
input.Take <= return.itemsPerPage
```

Observed examples:

```text
input.Take=-10; return.itemsPerPage=20
input.Take=1000; return.itemsPerPage=1000
```

Evaluation:

```json
{
  "status": "evaluated",
  "kind": "comparison:<=",
  "support_count": 2,
  "contradiction_count": 0,
  "unevaluated_count": 0,
  "summary": "Observed evidence check: all 2 evaluated example(s) satisfy the invariant; no observed contradiction found."
}
```

Why this matters:

- A model might incorrectly reason that a negative `Take` contradicts the
  invariant because `itemsPerPage` is positive.
- The deterministic check can show that `-10 <= 20` is actually true.
- If the model marks this false-positive for an impossible observed
  contradiction, the classifier can correct the result.

### Case 2: Observed Contradiction

Invariant:

```text
return.totalResults >= size(return.items[])
```

Observed examples:

```text
return.totalResults=1; size(return.items[])=2
return.totalResults=3; size(return.items[])=2
```

Evaluation:

```json
{
  "status": "evaluated",
  "kind": "comparison:>=",
  "support_count": 1,
  "contradiction_count": 1,
  "contradiction_examples": [
    "return.totalResults=1; size(return.items[])=2"
  ]
}
```

Classifier effect:

- If even one recovered example contradicts the invariant, the classifier can
  deterministically correct the row to `false-positive`.
- The reason will include the contradiction count and a concrete example.

This is stronger than an LLM-only judgment because the contradiction is directly
computed from observed assignments.

### Case 3: `one of` With Boolean Normalization

Invariant:

```text
return.isAct one of { 0, 1 }
```

Observed examples:

```text
return.isAct=false
return.isAct=true
```

Evaluation:

```json
{
  "status": "evaluated",
  "kind": "one_of",
  "support_count": 2,
  "contradiction_count": 0
}
```

Why this works:

- Daikon often renders booleans as `0` and `1`.
- JSON examples may contain `false` and `true`.
- `_value_key()` normalizes booleans to Daikon-compatible integer keys for this
  check.

Without this normalization, the checker could incorrectly treat valid boolean
examples as contradictions.

### Case 4: Unsupported Pattern

Invariant:

```text
return.date is a Date YYYY-MM-DD
```

Observed examples:

```text
return.date="2026-04-22"
```

Evaluation:

```json
{
  "status": "not-evaluated",
  "kind": "unsupported",
  "unevaluated_count": 1,
  "summary": "Observed evidence check: unsupported invariant pattern."
}
```

Classifier effect:

- No deterministic correction is applied.
- The LLM remains responsible for interpreting whether the spec and examples
  support the date-format invariant.

This conservative behavior avoids silently inventing deterministic logic for
patterns the code does not safely understand.

## SpecEnumAnalysis

`analyze_spec_enum_relationship(invariant, spec_excerpt)` returns
`SpecEnumAnalysis` for `one of` invariants.

| Field | Meaning |
| --- | --- |
| `status` | `not-applicable`, `no-enum`, `exact`, `subset`, or `conflict`. |
| `invariant_values` | Values listed by the Daikon `one of` invariant. |
| `spec_values` | Matching enum values found in the rendered spec excerpt. |
| `summary` | Human-readable explanation included in debug artifacts and prompt evidence. |

The checker only sees the rendered `spec_excerpt`, not the full OpenAPI spec.
That means enum analysis depends on `SpecExcerptBuilder` selecting the right
schema line.

## Spec Enum Examples

### Case 1: Exact Enum Match

Invariant:

```text
return.category one of { "books", "games" }
```

Rendered spec excerpt line:

```text
- response `items[].category`: string; enum=['books', 'games']
```

Evaluation:

```json
{
  "status": "exact",
  "invariant_values": ["books", "games"],
  "spec_values": ["books", "games"],
  "summary": "Spec enum check: invariant values exactly match the documented enum."
}
```

Classifier effect:

- If the LLM hallucinates that `"games"` is not documented, the classifier can
  correct the result to `true-positive`.
- This is a narrow correction: it applies because the invariant values exactly
  match the documented enum values.

### Case 2: Strict Subset

Invariant:

```text
return.category one of { "books" }
```

Rendered spec excerpt line:

```text
- response `items[].category`: string; enum=['books', 'games']
```

Evaluation:

```json
{
  "status": "subset",
  "invariant_values": ["books"],
  "spec_values": ["books", "games"],
  "summary": "Spec enum check: invariant is a strict subset of the documented enum; spec enum allows additional value(s): \"games\"."
}
```

Classifier effect:

- The invariant is narrower than the documented API contract.
- Even if observed examples only saw `"books"`, the spec says `"games"` is also
  valid.
- The classifier can correct an overconfident `true-positive` to
  `false-positive`.

### Case 3: Conflict

Invariant:

```text
return.category one of { "books", "music" }
```

Rendered spec excerpt line:

```text
- response `items[].category`: string; enum=['books', 'games']
```

Evaluation:

```json
{
  "status": "conflict",
  "invariant_values": ["books", "music"],
  "spec_values": ["books", "games"],
  "summary": "Spec enum check: invariant includes value(s) not documented in the enum: \"music\"."
}
```

Classifier effect:

- The invariant contains a value outside the documented enum.
- The classifier can correct the row to `false-positive`.

### Case 4: No Matching Enum

Invariant:

```text
return.status one of { "open", "closed" }
```

Rendered spec excerpt:

```text
- response `status`: string; Issue status
```

Evaluation:

```json
{
  "status": "no-enum",
  "invariant_values": ["open", "closed"],
  "summary": "Spec enum check: no matching documented enum found in the excerpt."
}
```

Classifier effect:

- No deterministic enum correction is applied.
- The LLM decides using the spec description, examples, and invariant type.

## What Breaks Without evidence_checker

Without `evidence_checker`:

- The LLM can misread numeric examples, especially comparisons involving
  negative values.
- The LLM can hallucinate enum contradictions even when the rendered spec line
  contains the enum.
- Observed contradictions would be buried in raw examples instead of exposed as
  explicit counts.
- Debug artifacts would lose `support_count`, `contradiction_count`, and
  `contradiction_examples`.
- More rows would become avoidable `false-positive` or `inconclusive` results.
- Prompt improvements alone would not fully prevent structured reasoning errors.

The key point: `evidence_checker` is not a general theorem prover. It is a small
set of deterministic guardrails for cases where the code can safely evaluate the
invariant against examples or documented enum values.

## How To Debug A Suspicious Row

When a classified row looks wrong:

1. Open `classification_debug/<row>.json`.
2. Check `normalized_context.parsed_program_point`.
   - Confirm the operation, status code, and response container path are right.
3. Check `spec_excerpt`.
   - Confirm the relevant request and response fields are visible.
4. Check `spec_excerpt_debug.budget_profile`.
   - Confirm the selected shape has enough request/response budget for the
     variables involved.
5. Check `spec_excerpt_debug.matched_schema_paths`.
   - Confirm the expected schema paths were actually rendered.
6. Check `examples`.
   - Confirm examples include the variables needed by the invariant.
7. Check `observed_evidence` and `spec_enum_evidence`.
   - If status is `not-evaluated` or `no-enum`, the LLM had to make the final
     judgment without deterministic support.
8. Check `deterministic_correction`.
   - If present, compare `previous_result` with the corrected `result`.

This workflow usually tells you whether the issue is:

- missing or incorrectly matched spec context;
- missing examples;
- unsupported deterministic evidence pattern;
- a real LLM reasoning error;
- or a legitimate `inconclusive` case.

## Known Boundaries

- Budgets improve focus, but they can still omit useful secondary context in
  complex schemas.
- `matched_schema_paths` shows rendered paths only, not every candidate that was
  considered and rejected.
- Observed evidence checks only cover supported expression patterns.
- Spec enum checks only work for `one of` invariants and enum lines present in
  the rendered excerpt.
- A deterministic correction should be interpreted as a targeted guardrail, not
  as a general proof that the invariant is semantically correct.

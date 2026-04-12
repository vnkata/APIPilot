import time
import uuid
from api_testing.prompts.request_response_constraint.schema import Verdict
from api_testing.utils.log import getLogger, logger


class RequestResponseConstraint:
    SYSTEM_PROMPT = """
You are given a set of request parameters and an API response schema. Your task is to infer constraints that describe how input parameters influence response properties, and express them using a formal, machine-readable Domain-Specific Language (DSL).
---
### Objective
For each single, pair, or triple of input parameters, identify whether they impose constraints on one or more response properties.
⚠️ **Only include constraints where BOTH `parameter` and `property` are present (non-null).**
Discard any constraint that does not map input parameters to specific response properties.
---
### DSL Specification
Use the following DSL primitives:
#### Logical operators
* `eq(a, b)`, `neq(a, b)`
* `gt(a, b)`, `gte(a, b)`, `lt(a, b)`, `lte(a, b)`
* `and(expr1, expr2, ...)`, `or(expr1, expr2, ...)`, `not(expr)`
* `implies(expr1, expr2)`
#### Set and domain
* `in(x, [v1, v2, ...])`
#### Existence
* `exists(x)`, `isNull(x)`
#### Functions
* `sizeOf(x)`
* `contains(x, y)`
#### API-specific predicates
* `isSortedBy(return, field, order)`
* `default(input.x, v)`
* `between(x, min, max)`
---
### Naming Convention
* Input parameters: `input.<param>`
* Response fields: `return.<field>`
* Nested fields: `return.a.b.c`
---
### Constraint Format
Return a JSON object:
```json
{
  "constraint": [
    {
      "parameter": "<param_list>",
      "predicate": "<DSL_expression>",
      "property": "<response_fields>"
    }
  ]
}
```
---
### Rules
* Each `parameter` must include all input parameters involved (single, pair, or triple).
* Each `property` must include all response fields involved.
* The predicate must be fully machine-readable using the DSL.
* Use `default(...)` when a parameter has a default value.
* Use `implies(...)` for conditional constraints.
* Use abstract predicates if needed, but only when they map to a concrete response property.
* Ensure input and output refer to the same concept when using `eq`.
* ❗ **Exclude any constraint where `property` is null or missing.**
---
### Output Requirement
Only return the JSON object following the specified format. Do not include explanations.
    """
    PROMPT = """
        Please review the following details for the endpoint and its associated parameters to identify the constraints needed for data retrieval:
        Endpoint: {endpoint}
        Description: {summary}
        Here is list parameters and response schema
        *Parameters:*
        {params}
        *Response schema:*
        {main_response}
        *Other subschemas responses:*
        {other_responses}
    """
    def __init__(self, llm):
        self.llm = llm
        self.logger = getLogger(__name__)


    def exec(self, *args, **kargs):
        print(args, kargs)
        prompt = self.PROMPT.format(*args, **kargs) ## pass
        self.logger.debug("RequestResponseConstraint Prompt: " + prompt)

        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            # schema=Verdict
        )
        self.logger.debug("RequestResponseConstraint Response: " + response)
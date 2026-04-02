import time
import uuid
from api_testing.prompts.request_response_constraint.schema import Verdict
from api_testing.utils.log import getLogger, logger


class RequestResponseConstraint:
    SYSTEM_PROMPT = """
**Refined Prompt (Filtered Constraints Only)**

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
    # SYSTEM_PROMPT = """
    # Given a set of request parameters and an API response schema, your task is to determine how each parameter influences the response. For each single, pair, or triple of request parameters, evaluate whether they constrain specific response properties.
    # Some cases can help determine a corresponding attribute:
    # - If the input parameter is null or omitted, the default value defined for the query parameter will be used (if a default is specified).
    # - The input parameter is used for filtering, and its corresponding attribute—representing the actual value after filtering—must exist within the same object as the input parameter.
    # - Constraints on input parameters—such as min, max, format, or allowed values (e.g., enum) - should align with the constraints of the corresponding response properties .For example, if input.limit ∈ (1, 2, 3) and input.limit = response.limit, then response.limit must also satisfy response.limit ∈ (1, 2, 3).
    # - The input parameter and the corresponding response attribute should represent the same concept and interpret their values consistently.
    # Eg:
    #     - ((input.limit or 20)  >= sizeOf(return)) and sizeOf(return) >= 0 and sizeOf(return) <= 100 # 20 is default value of input.limit
    #     - ((input.month or 1) = monthOfDay(return.date)) and (input.month >= 1 and input.month <=12)
    #     ....
    #     Returns a list of objects containing parameter, brief description, and property fields, representing how constraints are reflected in the JSON object. Each single, pair, or triple must consist of one or more input parameters, and each property must be one or more fields from the response schema.
    #     {
    #     "constraint": [
    #             {
    #             "parameter": "<param_list>",
    #             "predicate": "<logical_expression>",
    #             "property": "<response_fields>"
    #             }
    #         ]
    #     }
    # # IMPORTANT:
    # - The description specifies how many input parameters are required, and the parameter must include all of them.
    # - The description specifies how many return properties are required, and the property must include all of them.
    # """
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


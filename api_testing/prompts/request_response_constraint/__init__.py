import json
from .schema import Verdict
from api_testing.utils.log import getLogger


class RequestResponseConstraint:
    SYSTEM_PROMPT = """
You are given a set of request parameters and an API response schema. Your task is to infer constraints describing how input parameters influence response properties, and express them using a formal DSL.
---

### Objective

Identify constraints where **individual parameters or minimal necessary parameter groups** affect response fields.

* Prefer **single-parameter constraints** when possible.
* Only generate non-trivial constraints with a clear and meaningful relationship
* Only create **multi-parameter constraints when they jointly define one behavior** (e.g., sorting).
* Avoid redundant or overlapping constraints.

⚠️ Only include constraints where BOTH `parameter` and `property` are non-null.

---

### DSL Specification

Use:

**Logical**

* `eq, neq, gt, gte, lt, lte`
* `and, or, not, implies`

**Set**

* `in`

**Existence**

* `exists, isNull`

**Functions**

* `sizeOf, contains`

**API-specific**

* `isSortedBy(return, field, order)`
* `default(input.x, v)`
* `between`

---

### Key Rules (STRICT)

1. **No redundant constraints**

   * Do NOT generate both single and combined versions if one is sufficient.
   * Example: if sorting depends on both params → ONLY output one constraint with `"order_by, sort"`.

2. **Group parameters ONLY when necessary**

   * Use combined parameters **only if they jointly control one property**.
   * Example:

     ```
     isSortedBy(return, default(input.order_by,'created_at'), default(input.sort,'desc'))
     ```

3. **Inline default values**

   * Always use `default()` inside predicates.
   * ❌ Do NOT create separate default constraints.

4. **Use `implies(exists(...), ...)` for filters**

   * Except when behavior is unconditional (e.g., sorting).

5. **Property must be precise**

   * Include ALL response fields referenced in predicate.

6. **Avoid vague mappings**

   * Every constraint must clearly bind input → response field.

---

### Naming Convention

* Input: `input.x`
* Output: `return.field` (or nested)

---

### Output Format

```json
{
  "constraints": [
    {
      "parameter": "<param_list>",
      "predicate": "<DSL_expression>",
      "property": "<response_fields>"
    }
  ]
}
```
### DSL Examples
```json
{
  "constraints": [
    {
      "parameter": "id",
      "predicate": "implies(exists(input.id), eq(return.id, input.id))",
      "property": "return.id"
    },
    {
      "parameter": "status",
      "predicate": "implies(exists(input.status), eq(return.status, input.status))",
      "property": "return.status"
    },
    {
      "parameter": "id_after",
      "predicate": "implies(exists(input.id_after), gt(return.id, input.id_after))",
      "property": "return.id"
    },
    {
      "parameter": "id_before",
      "predicate": "implies(exists(input.id_before), lt(return.id, input.id_before))",
      "property": "return.id"
    },
    {
      "parameter": "created_after",
      "predicate": "implies(exists(input.created_after), gte(return.created_at, input.created_after))",
      "property": "return.created_at"
    },
    {
      "parameter": "created_before",
      "predicate": "implies(exists(input.created_before), lte(return.created_at, input.created_before))",
      "property": "return.created_at"
    },
    {
      "parameter": "q",
      "predicate": "implies(exists(input.q), or(contains(return.name, input.q), contains(return.description, input.q)))",
      "property": "return.name, return.description"
    },
    {
      "parameter": "category",
      "predicate": "implies(exists(input.category), eq(return.category, input.category))",
      "property": "return.category"
    },
    {
      "parameter": "tags",
      "predicate": "implies(exists(input.tags), in(input.tags, return.tags))",
      "property": "return.tags"
    },
    {
      "parameter": "limit",
      "predicate": "lte(sizeOf(return), default(input.limit, 20))",
      "property": "return"
    },
    {
      "parameter": "offset",
      "predicate": "implies(exists(input.offset), gte(sizeOf(return), 0))",
      "property": "return"
    },
    {
      "parameter": "order_by, sort",
      "predicate": "isSortedBy(return, default(input.order_by,'created_at'), default(input.sort,'desc'))",
      "property": "return"
    }
  ]
}```
### Expected Behavior (IMPORTANT)
* **Range filters** → define as separate constraints (e.g., `id_after`, `id_before`)
* **Time filters** → define as separate constraints
* **Access control** → use a single-parameter constraint
* **Sorting** → define as **one combined constraint using `default()`**
* **Search** → map to the appropriate text fields
**Field requirements:**
* `parameter`: Must be non-null, include all parameters used in the predicate, and start with `input`
* `property`: Must be non-null, include all response fields referenced in the predicate, and start with `return`
**General rules:**
* Avoid duplication and over-generation
* Remove any constraint where `parameter` or `property` is null or missing
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
        prompt = self.PROMPT.format(*args, **kargs) ## pass
        self.logger.debug("RequestResponseConstraint Prompt: " + prompt)

        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            schema=Verdict
        )
        # Filter out constraints where parameter is None
        self.logger.debug("RequestResponseConstraint Response: " +  response.model_dump_json(indent=2))
        return json.loads(response.model_dump_json(indent=2)) 

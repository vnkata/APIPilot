import json
from .schema import Verdict
from api_testing.utils.log import getLogger


class RequestResponseConstraint:
    SYSTEM_PROMPT = """
You are an expert API constraint mining system. Your objective is to infer behavioral invariants that map request parameters to their direct effects on API response properties. You must use the provided Domain Specific Language (DSL) strictly and output valid JSON.
### Core Directives
*   **Maximum Simplicity (Strict):** The DSL expression must be as simple and concise as possible. Avoid nesting redundant type-casting functions (toInt, toString, toBool) unless strictly necessary for data matching. Do not write verbose conditional logic if the behavior can be cleanly expressed using a single function.
*   **Focus on Behavior, Not Schema:** Generate constraints ONLY for parameter-driven behaviors (filtering, sorting, pagination, access control). DO NOT generate constraints for pure schema validation (e.g., checking if an ID is within min/max bounds or if a date is formatted correctly) unless it is conditionally driven by a parameter.
*   **Filter Logic (Inclusive vs. Exclusive):** Carefully distinguish between parameters that strictly filter (e.g., `status=active` means ALL returns must be active) and parameters that expand results (e.g., `include_optional=true` means optional items are allowed, but `include_optional=false` means they are strictly excluded). 
*   **Merge Defaults:** Use `default(input.x, fallback)` to represent both explicit and implicit parameter values in a single constraint. Do not generate separate constraints for parameter existence versus default fallbacks.
*   **Conditionals:** Use `implies(exists(input.x), ...)` for conditional behavior where defaults are not applicable.
*   **Strict Path Normalization:** Input paths must use `input.x`. Output paths must use `return.field` in standard dot notation. NEVER output array traversals like `[]`, `[*]`, or `[..]` in the `property` field (e.g., use `return.holidays.federal`, NOT `return.holidays[*].federal`).
*   **One Property per Constraint:** Each response property may appear in at most one constraint. Prefer single-parameter constraints.
*   **DSL Adherence:** Use ONLY the provided DSL functions and operators. Never invent syntax, helpers, or ternary operators. If a behavior cannot be expressed in this DSL, omit it entirely.

### DSL Signatures
*   **Logical:** `eq(a,b)`, `neq(a,b)`, `gt(a,b)`, `gte(a,b)`, `lt(a,b)`, `lte(a,b)`, `and(...)`, `or(...)`, `not(expr)`, `implies(cond,expr)`
*   **Set:** `in(value, collection)`
*   **Functions:** `sizeOf(collection)`, `contains(text,value)`, `substring(text,start,length)`, `exists(value)`, `default(value,fallback)`, `toBool(value)`, `toInt(value)`, `toString(value)`
*   **API:** `isSortedBy(collection,field,order)`, `isDate(value)`, `isTime(value)`, `isDateTime(value)`, `isEmail(value)`, `isURL(value)`, `between(value,min,max)`, `isRegex(value,pattern)`

### Output Format
```json
{
  "constraints": [
    {
      "parameter": "input.<field>",
      "predicate": "<The simplest, most concise DSL expression possible referencing both parameter and property>",
      "property": "return.<field>"
    }
  ]
}

```
### 💡 Examples of Good Constraints
1. **Filtering by ID:**
`{ "parameter": "input.id", "predicate": "implies(exists(input.id), eq(return.id, input.id))", "property": "return.id" }`
2. **Filtering by Date (Default Applied):**
`{ "parameter": "input.year", "predicate": "contains(return.date, toString(default(input.year, 2026)))", "property": "return.date" }`
3. **Pagination Limit:**
`{ "parameter": "input.limit", "predicate": "lte(sizeOf(return), default(input.limit, 20))", "property": "return" }`
4. **Exclusive Boolean Filter (e.g., exclude hidden items if false):**
`{ "parameter": "input.hidden", "predicate": "implies(not(toBool(default(input.hidden, 'false'))), neq(return.visibility, 'hidden'))", "property": "return.visibility" }`
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
            schema=Verdict,
            caller=self.__class__.__name__,
        )
        # Filter out constraints where parameter is None
        self.logger.debug("RequestResponseConstraint Response: " +  response.model_dump_json(indent=2))
        return json.loads(response.model_dump_json(indent=2)) 

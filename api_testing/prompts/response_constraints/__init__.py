import json
from time import sleep
from api_testing.utils.log import getLogger
from .schema import Verdict
class ResponseConstraints:
#   SYSTEM_PROMPT = """
# You are given a schema and its attributes. Identify any constraints, rules, or limitations implied by each attribute’s description. Confirm that the description contains enough information to support automated validation of these constraints.
# Follow these steps below to complete your task:
# **STEP 1**: Review the provided schema and its attributes. Briefly describe the purpose or function of each attribute based on its definition or description.
# **STEP 2**: From STEP 1, identify attributes whose name and descriptions imply constraints, rules, or limits that can be programmatically verified:
# - Semantic inference: Constraints can be inferred from the attribute’s name and description based on their common or contextual meaning.
# - General: Descriptions defining specific values, ranges, formats, or logic indicate constraints.
# - Format: Mention or imply URI/URL, timestamp (ISO 8601), email, slug, date, datetime, version, or schema hints like format: uri, format: date-time.
# - Enum: Fixed value sets (e.g., “one of public, private”).
# - Range: Numeric or string limits (e.g., “≤255”, “1–10”, “max length 32”).
# - Ignore vague terms: “recommended”, “typically”, “usually” are not constraints unless precise.
# - Examples: Examples showing valid formats (URL, date, etc.) imply constraints if consistent.

# FINAL OUTPUT:
# The response is in the format below, no explanation is needed:
# ```json {
#   "constraints": ["attribute_name_1","attribute_name_2"]
# }```
# """
  SYSTEM_PROMPT = """
You are a Data Engineering and Schema Architecture expert. Analyze a schema to identify programmatically validatable constraints from property semantics, and express them in a formal DSL.
### Task
**Step 1:** Understand each property’s purpose from its name and description; infer relationships when clearly implied.
**Step 2:** Extract constraints only when clearly justified—explicitly stated or unambiguously implied by structured fields (e.g., fixed length, positional, composite IDs) with consistent mappings. Consider relationships across sibling and nested fields, deriving constraints only when stable and unambiguous.
*For encoded fields:* Identify multi-part structures (e.g., positional semantics) and map components via substring/position logic; use `eq` for exact, guaranteed mappings, and `implies` for partial or uncertain ones—defaulting to `implies` when not fully certain.
### Rules
* **Semantic inference:** e.g., IDs → `> 0`, counts → `≥ 0`, positions → `≥ 1`
* **Explicit rules:** defined values, ranges, formats, logic
* **Inter-field dependencies:** encoding, derivation, subset relations
* **Formats:** URL, date, email, slug, version, etc.
* **Enum / Range:** fixed sets, bounds, lengths
### Constraint combination rule:
When a field has both intrinsic constraints (derived from its own description, type, or value range) and inferred constraints (derived from relationships with other fields), you MUST preserve and combine both using `and`.
- Intrinsic constraints MUST always be enforced unconditionally.
- Inferred or cross-field constraints MUST be expressed using `implies`, unless the mapping is exact and type-safe.
- NEVER overwrite or omit intrinsic constraints when adding inferred constraints.
- If there is any uncertainty in mapping (e.g., substring extraction, type mismatch like string vs integer), prefer `implies` over `eq`.
### DSL
* Logical: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `and`, `or`, `not`, `implies`
* Set: `in`
* Functions: `sizeOf`, `contains`
* API: `isSortedBy`, `isDate`, `isEmail`, `isUrl`,`between`, `isRegex`,etc. 
**Format enforcement rule:**
* Use `isRegex` when a **specific pattern (e.g., https, fixed format, exact structure)** is explicitly defined.
* Use `isUrl`, `isDate`, etc. only for **general format validation** when no stricter pattern is provided.
* When both exist, **prioritize `isRegex` or combine them with `and` if needed for stricter validation**.
### Output
```json
{
  "constraints": {
    "property_1": "<DSL_expression>" ## DSL_expression must be concise yet comprehensive. eg: `implies(not(eq(type, 'ROH')), eq(typeEstimated.category, substring(type, 0, 1)))`
  }
}
```
DSL Examples:
{
  "constraints": {
    "id": "gt(id, 0)",
    "status": "in(status, ['ACTIVE','INACTIVE'])",
    "email": "isEmail(email)",
    "url": "and(isUrl(url), isRegex(url, '^https://.*$'))",
    "startDate": "isDate(startDate)",
    "endDate": "and(isDate(endDate), gte(endDate, startDate))",
    "code": "and(isRegex(code, '^[A-Z0-9]{3}$'), eq(sizeOf(code), 3))",
    "items": "gt(sizeOf(items), 0)",
    "sortedList": "isSortedBy(sortedList, 'date')",
    "compositeField": "implies(exists(parent), eq(child, substring(parent, 0, 2)))"
  }
}
"""
  PROMPT = """
Please review the following details for the schema and its attributes:
Schema: {schema}
Properties:
{properties}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  
  def exec(self, *args, **kargs):
        prompt = self.PROMPT.format(*args, **kargs) ## pass
        self.logger.debug("ResponseConstraint Prompt: " + prompt)

        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            schema=Verdict
        )
        # Filter out constraints where parameter is None
        self.logger.debug("ResponseConstraint Response: " +  response.model_dump_json(indent=2))
        return response.constraints
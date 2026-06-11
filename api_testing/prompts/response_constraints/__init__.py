import json
from time import sleep
from api_testing.utils.log import getLogger
from .schema import Verdict
class ResponseConstraints:
  SYSTEM_PROMPT = """
**You are a Data Engineering and Schema Architecture expert. Analyze the provided schema to extract programmatically validatable constraints and express them in a formal DSL.**
### Execution Steps 
* **Step 1 (Analyze):** Understand each property's purpose from its name and description; infer implied relationships.
* **Step 2 (Validate):** Extract constraints *only* when strictly justified or unambiguously implied (e.g., positional encoding, composite IDs). Use `implies` for uncertain/partial mappings, and `eq` for exact, type-safe rules.
* **Step 3 (Translate):** Convert finalized natural-language rules into precise, machine-readable DSL expressions.
* **Step 4 (Judge & Verify):** Rigorously audit every generated JSON key and DSL expression against the Core Rules before rendering the final output. 
Double-check that:
- All properties listed in a multi-property k ey are explicitly used inside the DSL expression.
- The expression is in its absolute simplest, most concise form.
- No intrinsic single-field rules were overwritten or omitted when combining constraints. If any expression violates these criteria, loop back and rewrite it before finalized delivery.
### Core Rules
* **Semantic Inference:** Automatically infer bounds based on context (e.g., IDs `> 0`, counts `≥ 0`, positions `≥ 1`).
* **Constraint Combination:** Intrinsic constraints (single field limits) MUST be enforced unconditionally. Combine intrinsic and cross-field constraints using `and(...)`. **Never overwrite or omit intrinsic rules.**
* **Simplicity & Conciseness:** The generated DSL must be the simplest, most concise expression possible while accurately referencing all relevant properties.
* **Format Enforcement:** Prioritize `isRegex` for specific/strict patterns. Use general functions (`isDate`, `isURL`) only for fallback validation. Combine via `and` if necessary.
* **Multi-Property Keys:** If a constraint references multiple properties, you MUST list all referenced properties in the key as a comma-separated string.
### DSL Signatures
* **Logical:** `eq(a,b)`, `neq(a,b)`, `gt(a,b)`, `gte(a,b)`, `lt(a,b)`, `lte(a,b)`, `and(...)`, `or(...)`, `not(expr)`, `implies(cond,expr)`
* **Set & String:** `in(val, list)`, `sizeOf(list)`, `contains(txt,val)`, `substring(txt,start,length)`
* **Validation & Utils:** `isDate(val)`, `isTime(val)`, `isDateTime(val)`, `isEmail(val)`, `isURL(val)`, `isRegex(val,pattern)`, `exists(val)`, `default(val,fallback)`, `toBool(val)`, `toInt(val)`, `toString(val)`, `isSortedBy(list,field,order)`, `between(val,min,max)`
<The DSL must simplest, most concise DSL expression possible referencing all property>
### Output Format
Output valid JSON only, following this structure:

```json
{
  "constraints": {
    "id": "gt(id, 0)",
    "status": "in(status, ['ACTIVE','INACTIVE'])",
    "code": "and(isRegex(code, '^[A-Z0-9]{3}$'), eq(sizeOf(code), 3))",
    "url": "and(isURL(url), isRegex(url, '^https://.*$'))",
    "endDate,startDate": "gte(endDate, startDate)",
    "typeEstimated.category,type": "implies(not(eq(type, 'ROH')), eq(typeEstimated.category, substring(type, 0, 1)))"
  }
}
```
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
            schema=Verdict,
            caller=self.__class__.__name__,
        )
        # Filter out constraints where parameter is None
        self.logger.debug("ResponseConstraint Response: " +  response.model_dump_json(indent=2))
        return response.constraints
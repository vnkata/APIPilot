


from .schema import (
    Verdict
)
from api_testing.utils.log import getLogger


class ConstraintArbitration:

    SYSTEM_PROMPT = """
You are an assistant whose task is to classify the relationship between two constraints for the same API property.
You will be given:

* API specification (OpenAPI): type, format, enum, min/max, description
* Two constraints for the same property:

  1. Constraint A (from specification)
  2. Constraint B (from dynamic runtime)

### Internal Reasoning Steps
When making your decision, internally perform the following:

1. **Understand the property**

   * Identify the property type, format, allowed values, and semantic meaning from the API specification.
   * Infer the intended domain of valid values.

2. **Normalize both constraints**

   * Rewrite Constraint A and Constraint B into comparable logical forms.
   * Convert ranges, enums, regexes, predicates, or textual conditions into explicit sets or conditions when possible.

3. **Compare the valid value spaces**

   * Determine the relationship between the value sets allowed by Constraint A and Constraint B.

4. **Classify the relationship**
Use one of the following categories:

* **Equivalent**
  Both constraints allow exactly the same set of values.

* **Subset**
  One constraint allows a strict subset of the values allowed by the other constraint.
  In other words, one constraint is strictly more restrictive than the other.

  Example:
  - A: integer ≥ 0
  - B: integer ≥ 10
  → B is a subset of A.

* **Intersection**
  The constraints partially overlap, but neither constraint fully contains the other.

  Example:
  - A: integer between 1 and 10
  - B: even integers between 2 and 20
  → overlap exists, but neither is a subset of the other.

* **Disjoint (Conflicting)**
  The constraints have no overlapping valid values and cannot both be true simultaneously.

  Example:
  - A: string enum {"A", "B"}
  - B: string enum {"C", "D"}
5. **Prioritize semantic meaning**

   * Do not rely only on syntax.
   * Consider descriptions, naming, formats, and implied business rules.

6. **Handle uncertainty carefully**

   * If the relationship cannot be determined precisely, choose the closest conservative classification and explain why.

### **Output Format (STRICT)**
Return ONLY:
```json
{
  "datas": [
    {
      "id": "<index of the invariant (starting from 1)>",
      "answer": <1 = Equivalent, 2 = Subset, 3 = Intersection, 4 = Disjoint>
    }
  ]
}
```
"""

    PROMPT = """
Is the following constraints for a REST endpoint better represented by OpenAPI specification or dynamic runtime observation?
Endpoint: {endpoint}
Description: {summary}
Parameters:
{parameters}
Responses:
{responses}
Constraints: 
{constraints}
"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.logger = getLogger()

    def exec(self, *args, **kargs):
        prompt = self.PROMPT.format(*args, **kargs) ## pass
        self.logger.debug("ConstraintArbitration Prompt: " + prompt)
        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            schema=Verdict
        )
        self.logger.debug("ConstraintArbitration Response: " + response.model_dump_json(indent=2))
        return response.datas
    

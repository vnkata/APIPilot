


from .schema import (
    Verdict
)
from api_testing.utils.log import getLogger


class ConstraintArbitration:

    SYSTEM_PROMPT = """
You are an assistant that evaluates which constraint better represents the true behavior of a REST API property.
You will be given:
* API specification (OpenAPI): type, format, enum, min/max, description
* Two constraints for the same property:
  1. Constraint A (from specification)
  2. Constraint B (from dynamic runtime)
---
### **Internal Reasoning Steps**
    When making your decision, internally perform:
    1. **Understand the property**
    * Identify its type, domain, and meaning from the API spec
    2. **Validate each constraint independently**
    * Does it match the type?
    * Does it align with the semantic meaning of the property?
    * Could it hold for all valid API responses?
    3. **Check generalization**
    * Is the constraint universal or derived from limited observations?
    * Does it overfit to specific values?
    4. **Compare reliability**
    * OpenAPI = intended contract
    * Runtime = observed behavior (may be incomplete)
    5. **Detect issues**
    * Overly specific values → likely runtime artifact
    * Cross-field comparisons without meaning → invalid
    * Type mismatch → invalid
---
### **Decision Rule**
* Prefer the constraint that is:
  * Semantically correct
  * Type-consistent
  * Valid for ALL possible valid responses
  * Not overfitted to sample data
---
### **Output Format (STRICT)**
Return ONLY:

```json
{
  "datas": [
    {
      "id": "<index of the invariant (starting from 1)>",
      "answer": <1 for specification constraint or 2 for runtime constraint, indicating which constraint is better>
    }
  ]
}
```
### **Important Notes**
* Do NOT output internal reasoning steps
* Do NOT include chain-of-thought
* Keep reasoning concise but meaningful
* If runtime constraint is overly specific or suspicious → prefer OpenAPI
* If OpenAPI is vague but runtime captures a true invariant → prefer runtime
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
    

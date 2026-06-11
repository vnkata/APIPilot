


from .schema import (
    Verdict
)
from api_testing.utils.log import getLogger


class ConstraintArbitration:

    SYSTEM_PROMPT = """
You are an expert API constraint analyst. Classify the semantic logical relationship between Constraint A (spec-derived) and Constraint B (runtime-derived) using a strict Chain of Thought (CoT) process.
**Analysis Steps:**
1. **Analyze expected outputs:** Determine and compare the exact set of valid values accepted by Constraint A and Constraint B, leveraging the provided API metadata.
2. **Classify:** Determine the logical relationship based on the value sets.
**Rules:**
* Normalize constraints first (remove tautologies/duplicates, flatten operators).
* Prioritize semantic implication over syntactic similarity. 
* "Subset" takes priority over "Intersection" if a logical implication exists.
**Classifications:**
* **1 = Equivalent**: Both accept exactly the same valid values.
* **2 = Subset**: One is strictly stronger/more restrictive than the other.
* **3 = Intersection**: Partial overlap, but neither implies the other.
* **4 = Disjoint**: Zero common valid values.
Return ONLY the following JSON structure. Do not include any external markdown prose or explanations.
{
  "datas": [
    {
      "id": "<index>",
      "answer": <1|2|3|4>
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
            schema=Verdict,
            caller=self.__class__.__name__,
        )
        self.logger.debug("ConstraintArbitration Response: " + response.model_dump_json(indent=2))
        return response.datas
    

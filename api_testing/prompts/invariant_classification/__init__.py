


from .schema import (
    Verdict
)
from api_testing.utils.log import getLogger


class InvariantClassification:

    SYSTEM_PROMPT = """
You are an assistant that evaluates whether a given invariant is correct for a REST API. Your task is to classify each invariant as **"true-positive"** (holds for every valid request) or **"false-positive"** (does not hold universally), and provide a brief justification.
You will receive a list of invariants extracted from a REST API endpoint, along with endpoint details (path, HTTP method, description, input parameters, and response fields).
Each invariant is a logical expression involving request (`input.*`) and/or response (`return.*`) fields. For every invariant, you are given expression, type and description. You must carefully read and rely on the invariant description to understand its intended meaning before making a decision. Do not judge based on the expression alone.
Classify each invariant as:
* **true-positive**: holds for all valid requests
* **false-positive**: does not hold universally
Provide a brief justification.
**Notes:**
* `input.*` = request fields
* `return.*` = response fields
**Rules:**
* **You must carefully read and rely on the invariant description to understand its intended meaning before making a decision.** Do not judge based on the expression alone. (IMPORTANT)
* Variables must be semantically related and meaningfully comparable
* Ensure type compatibility; comparisons involving mismatched types—especially real integers vs. boolean-like fields (0/1)—must be classified as **false-positive**
* Reject nonsensical or misleading comparisons (e.g., `id > count`, or unclear comparisons between real integers and boolean-like fields) → **false-positive**
* For boolean-like fields, only accept invariants that always hold under valid API logic; otherwise → **false-positive**
* Keep only invariants that reflect consistent and valid API behavior

**FINAL OUTPUT (strict format):**

```json
{
  "datas": [
    {
      "id": "<index of the invariant (starting from 1)>",
      "classification": "true-positive" or "false-positive"
    }
  ]
}
```
""".strip()

    PROMPT = """
Is the following invariants for a REST endpoint "true - positive" or "false - positive"?
Endpoint: {endpoint}
Description: {summary}
Parameters:
{parameters}
Responses:
{responses}
Invariants: 
{invariants}
The invariant is classified as "true - positive" if it holds for every valid request on the API, and "false - positive" if it does not hold for every valid request on the API.
""".strip()

    def __init__(self, llm) -> None:
        self.llm = llm
        self.logger = getLogger()

    def exec(self, *args, **kargs):
        prompt = self.PROMPT.format(*args, **kargs) ## pass
        self.logger.debug("InvariantClassification Prompt: " + prompt)
        response, _ = self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            prompt=prompt,
            schema=Verdict,
            caller=self.__class__.__name__,
        )
        self.logger.debug("InvariantClassification Response: " + response.model_dump_json(indent=2))
        return response.datas
    

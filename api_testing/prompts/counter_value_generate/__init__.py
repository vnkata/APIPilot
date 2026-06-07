import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class CounterValueGenerate:
  SYSTEM_PROMPT = """
Given an API endpoint and its payload definitions from an OpenAPI specification, generate **counter-example JSON test data** for all request components.
Each response should follow this structure, Dont explain anything, just return the JSON array:
```json
{
  "datas": [
    {
      "parameters": { "parameter1": "value1", ..., "parameterN": "valueN" },
      "requestBody": { "field1": "value1", ..., "fieldN": "valueN" },
      "expected_code": "<expected HTTP response code: '2xx' or '4xx'>, only generate 2xx if the counterexample is valid for the OpenAPI spec but violates the hypothesis",
      "hypothesis": "<1 for hypothesis 1 or 2 for hypothesis 2>"
    },
    ...
  ]
}
```
Here's a clearer and more precise rewrite:

### Requirements
* **If the relation is `Subset`**, generate counterexamples that satisfy the **superset** hypothesis but violate the **subset** hypothesis. The generated values should lie outside the subset domain, demonstrating that the two hypotheses are not in a subset relationship.
* **If the relation is `Intersection`**, generate counterexamples that satisfy one hypothesis while violating the other. The generated values should demonstrate that the two hypotheses are not fully overlapping and therefore cannot be considered subsets of each other.
* **If the relation is `Disjoint`**, generate counterexamples that satisfy one hypothesis while violating the other. The generated values should demonstrate overlap between the hypotheses, showing that they are not truly disjoint.
* **If no relation is provided**, generate counterexamples that independently violate each hypothesis.
* Base all generated valid values on examples and patterns observed in the OpenAPI specification to ensure realistic and contextually **valid test data**.
"""
  PROMPT = """
Analyze the following endpoint definition and parameter details, then produce {num_test_cases} counterexample values for every request component.
Endpoint: {endpoint}
Description: {summary}
Parameters: 
{specific_endpoint_params}
{request_body_part}
Hypothesis for properties {property}: 
hypothesis 1: {hypothesis_1}
hypothesis 2: {hypothesis_2}
Relation between the two hypotheses (if any): {relation} 
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  
  def exec(self, *args, **kwargs):
    body = kwargs.get("specific_endpoint_body")
    request_body_part = f"Request Body Schema:\n{body}" if body else ""
    prompt = self.PROMPT.format(request_body_part=request_body_part, **kwargs) ## pass
    self.logger.debug("CounterValueGenerate Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("CounterValueGenerate Response: " + response.model_dump_json(indent=2))
    return response
  
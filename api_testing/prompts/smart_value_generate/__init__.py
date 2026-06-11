import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class SmartValueGenerate:
  SYSTEM_PROMPT = """
Given an API endpoint and its payload definitions from an OpenAPI specification, generate **context-aware JSON test data** for all request components.
Each response should follow this structure:
```json
{
  "datas": [
    {
      "parameters": { "parameter1": "value1", ..., "parameterN": "valueN" },
      "requestBody": { "field1": "value1", ..., "fieldN": "valueN" },
      "expected_code": "<expected HTTP response code: '2xx' or '4xx'>"
    },
    ...
  ]
}
```
### Requirements
1. Include all **required fields**, and selectively omit optional ones across requests.
2. Use **example** and **enum** values where available, and infer realistic ones from **descriptions** when not.
3. Generate both **valid** and **intentionally invalid** data items based on the specification:
   * **Missing required fields:** omit one or more required fields (until all are missing).
   * **Wrong data types:** replace field types using the rules below:
     * string → number / boolean / array
     * integer → string / boolean / array
     * boolean → string / number / array
     * array → string / number / boolean
     * object → string / number / boolean / array
   * **Constraint violations:** break constraints like `pattern`, `format`, or numeric/length limits (e.g., invalid regex, out-of-range values, malformed date-time).
Base all generated values on example data from the OpenAPI specification to maintain realistic context.
"""
  PROMPT = """
Please review the following details for the endpoint components from its OpenAPI Specification, generate {num_test_cases} valid values for all request components:
Endpoint: {endpoint}
Description: {summary}
Parameters: 
{specific_endpoint_params}
{request_body_part}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  
  def exec(self, *args, **kwargs):
    body = kwargs.get("specific_endpoint_body")
    request_body_part = f"Request Body Schema:\n{body}" if body else ""
    prompt = self.PROMPT.format(request_body_part=request_body_part, **kwargs) ## pass
    self.logger.debug("SmartValueGenerate Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict,
      caller=self.__class__.__name__,
    )
    self.logger.debug("SmartValueGenerate Response: " + response.model_dump_json(indent=2))
    return response
  
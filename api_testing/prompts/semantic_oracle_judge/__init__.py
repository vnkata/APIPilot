from api_testing.utils.log import getLogger

from .schema import Verdict


class SemanticOracleJudge:
  SYSTEM_PROMPT = """
You are a API Testing Expert. Your task is evaluate whether the request satisfies the API constraints.
You are provided with the following information:
1. A method, endpoint, parameters and request body 
2. A list of test data
## Tasks
Evaluate whether each request satisfies API constraints. Based on this information, you need to:
* Populate all fields marked as **LLMGenerator** with concrete, realistic values so that the resulting request conforms to the specified `expected_code`. Don't change struct response
* Keep "idx","parameters", "requestBody", and "expected_code" EXACTLY unchanged (no normalization, no type changes). Preserve requestBody structure (object stays object, including "__body__").
* If `expected_code` is "2xx", verify that the request satisfies all API constraints (e.g., type, format, required fields, dependencies, inter-parameter relationships, mutual exclusion, combination rules,...). Return `1` if valid; otherwise `0`.
* If `expected_code` is "4xx", set satisfies = 1 without evaluating the constraints.
## Important
- If `expected_code` is "2xx" and a test case is missing required parameters or a required request body, add the missing fields using valid values that comply with the specification.
- Only populate fields that already exist in each test case. Do not add any new fields under any circumstances. If a field must be included, it must already exist and be filled with a realistic value.
## FINAL OUTPUT
Return ONLY valid JSON with the exact same structure as the input. The response must follow the format below. No explanation is needed. Return only requests where satisfies = 1:
```json {
  "datas": [
    {
      "idx": "...",
      "parameters": { "parameter1": "value1", ..., "parameterN": "valueN" },
      "requestBody": { "field1": "value1", ..., "fieldN": "valueN" }, 
      "expected_code": "<expected HTTP response code: '2xx' or '4xx'>",
      "satisfies": "<1 or 0>"
    },
    ...
  ]
}```
"""
  PROMPT = """
Please review the following details for the endpoint and its associated parameters and request body to evaluation:
Endpoint: {endpoint}
Description: {summary}
Parameters:
{parameters}
Request Body:
{requestBody}
** TEST DATAS: **  
{test_datas}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  def exec(self, *args, **kargs):
    prompt = self.PROMPT.format(*args, **kargs) ## pass
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict,
      caller=self.__class__.__name__,
    )
    self.logger.debug("SemanticOracleJudge Response: " + response.model_dump_json(indent=2))
    return response
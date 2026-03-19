from logging import getLogger

from .schema import Verdict


class SemanticOracleJudge:
  SYSTEM_PROMPT = """
You are a API Testing Expert. Your task is evaluate whether the request satisfies the API constraints.
You are provided with the following information:
1. A method, endpoint, parameters and request body 
2. A list of test data
Tasks
Evaluate whether each request satisfies API constraints. Based on this information, you need to:
* Fill the fields marked as **LLMGenerator** with concrete values so that the final request aligns with the specified **expected_code**.
* If `expected_code` is `"2xx"`, verify that the request satisfies all API constraints (e.g., type, format, required fields, dependencies, inter-parameter relationships, mutual exclusion, combination rules,...). Return `1` if valid; otherwise `0`.
* If `expected_code` is "4xx", set satisfies = 1 without evaluating the constraints.
FINAL OUTPUT:
The response must follow the format below. No explanation is needed. **Return only requests where `satisfies` = 1**:
```json {
  "datas": [
    {
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
    self.logger.debug("SemanticOracleJudge Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("SemanticOracleJudge Response: " + response.model_dump_json(indent=2))
    return response
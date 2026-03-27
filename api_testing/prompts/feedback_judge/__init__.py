import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class FeedBackJudge:
  """LLM-based judge for analyzing failed API requests and determining corrective actions."""
    
  SYSTEM_PROMPT = """
You are an **API Testing Expert**. Analyze API requests that returned a **4xx Client Error** and determine the appropriate corrective action.
### Inputs
1. **Executed Workflow Steps** – previously executed API operations.
2. **Current Operation Specification** – endpoint, description, parameters, parameter sources, and request body schema.
3. **Failed Requests** – an array of failed requests (method, url, path_params, query_params, request_body, error_response).
### Task
For each failed request, determine the most probable cause by analyzing resource relationships, parameter sources, and constraints.You must carefully evaluate all possibilities before deciding.
- **invalid_resource_pair** → invalid combination of path parameters (IDs from unrelated resources).
- **constraints** → parameter constraint violation (format, range, missing value, etc.).
- **invalid_parameter_source** → parameter value derived from the wrong resource field.
### Reasoning Instructions (Important)
- Think through the problem step by step internally before answering
- Consider multiple possible causes (e.g., constraint violation, resource mismatch, incorrect source)
- Cross-check against:
  - Executed Workflow Steps
  - Parameter Sources
  - Error message semantics
- If the error indicates “resource not found”, prioritize:
  - resource relationship mismatch
  - incorrect parameter pairing
- Only report constraints or invalid_parameter_source when there is clear evidence
- Choose the most specific and highest-confidence cause
Do not include your reasoning. Return only the final result.
### Response
Return **only** the following JSON:
```json
{
  "datas": [
    {
      "invalid_resource_pair": true/false,
      "constraints": {
        "param1": "updated constraint description"
      },
      "invalid_parameter_source": {
        "param1": "correct_resource_property" 
      }
    }
  ]
}
"""
  USER_PROMPT_TEMPLATE  = """
### Provided Inputs:
**Executed Workflow Steps**
{test_sequences}
**Current Operation Specification**
Endpoint: {endpoint}
Description: {summary}
Parameters:
{parameters}
Parameter Sources:
{parameters_sources}
Request Body:
{requestBody}
**Failed Requests**
{operations_details}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)
  
  def exec(self, *args, **kwargs):
    prompt = self.USER_PROMPT_TEMPLATE.format(*args, **kwargs) ## pass
    self.logger.debug("FeedBackJudge Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("FeedBackJudge Response: " + response.model_dump_json(indent=2))
    return json.loads(response.model_dump_json(indent=2)) 
import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class SmartValueGenerate:
  SYSTEM_PROMPT = """
Given an API endpoint and its payloads from an OpenAPI specification, Generate context-aware and valid values for all request components.
Return the answer as a JSON object with the following structure:
{
  "datas": [
    {
      "parameters": { "parameter1": "value1",..., "parameterN": "valueN"},
      "requestBody": { "field1": "value1", ..., "fieldN": "valueN" }
    },
    ...
    {
      "parameters": { "parameter1": "value1",..., "parameterN": "valueN"},
      "requestBody": { }  // empty dict if the endpoint hasn't request body
    }
  ]
}
Always include all required fields while selectively omitting optional ones across all request components.
Use provided examples and enum values when available, and rely on descriptions—not just constraints—for accuracy.
"""
  PROMPT = """
Please review the following details for the endpoint components from its OpenAPI Specification, generate {no_requested} valid values for all request components:
Endpoint: {endpoint}
Description: {summary}
Parameters: 
{specific_endpoint_params}
Request Body Schema: {specific_endpoint_body}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  
  def exec(self, *args, **kargs):
    prompt = self.PROMPT.format(*args, **kargs) ## pass
    self.logger.debug("SmartValueGenerate Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("SmartValueGenerate Response: " + response.model_dump_json(indent=2))
    return response
  
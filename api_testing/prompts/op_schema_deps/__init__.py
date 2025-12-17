import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class OpSchemaDeps:
  SYSTEM_PROMPT = """
Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.
Follow these steps below to complete your task:
**STEP 1**: Review the provided API endpoint and describe each parameter briefly based on its function or purpose.
**STEP 2**: From **STEP 1**, review the provided API endpoint, its parameters, and brief descriptions to identify and select only those parameters that serve as direct identifiers or foreign keys for a specific entity, excluding generic or contextual filtering parameters. Apply the same process to the attributes of each data schema.
**STEP 3**: From **STEP 2**, review the data schemas and their attributes to identify potential matches for each endpoint parameter key. Then, map each parameter to the schema attribute(s) that can most accurately provide the required information.
**IMPORTANT**: The parameter and schema attribute must either share the same data type or be of an array type.
FINAL OUTPUT:
The response is in the format below, no explanation is needed:
```json {
  "schema_1": {
    "parameter_name_1": "attribute_name_1, attribute_name_2",
    "parameter_name_2": "attribute_name_3, attribute_name_4"
  }
}```
"""
  PROMPT = """
Please review the following details for the endpoint and its associated parameters to identify the corresponding schemas needed for data retrieval:
Endpoint: {endpoint}
Description: {summary}
Specific Endpoint Parameters:
{specific_endpoint_params}
Additionally, you are provided with a list of all data schemas and their attributes as described in the Swagger Specification of the API application:
{data_schemas}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  
  def exec(self, *args, **kargs):
    prompt = self.PROMPT.format(*args, **kargs) ## pass
    self.logger.debug("OpSchemaDeps Prompt: " + prompt)
    for i in range(3):  # Thử lại tối đa 3 lần nếu không lấy được JSON hợp lệ
      try:
        response, _ = self.llm.generate(
          system_prompt=self.SYSTEM_PROMPT,
          prompt=prompt,
          # schema=Verdict
        )
        self.logger.debug("OpSchemaDeps Response: " + response)
        
        start, end  = -1, -1
        # start = response.find('json') 
        start = response.find('{') # vị trí dấu { đầu tiên 
        end = response.rfind('}') # vị trí ``` cuối cùng
        if start != -1 and end != -1:
          json_str = response[start:end+1].strip()   
          data = json.loads(json_str) # response mapping
          return data
      except:
        sleep(20)
        print("Retrying...", i+1)
        pass
    return {}
  
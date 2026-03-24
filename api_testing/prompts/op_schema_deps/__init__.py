import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class OpSchemaDeps:
  SYSTEM_PROMPT = """
Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.
Follow these steps below to complete your task:
**STEP 1**: Review the provided API endpoint and describe each parameter briefly based on its function or purpose.
**STEP 2**: Review the data schemas and retain only the primary and foreign keys.
**STEP 3**: From **STEP 1**, review the provided API endpoint, its parameters, and brief descriptions to identify and select only those parameters that serve as direct identifiers or foreign keys for a specific entity in **STEP 2**, excluding generic, descriptive, configuration or contextual filtering parameters.
**STEP 4**: From **STEP 2**, review the data schemas and their attributes to identify potential matches for each endpoint parameter key in **STEP 3**. Then, map each parameter to the schema attribute(s) that can most accurately provide the required information.
- When multiple schemas have similar structures or share the same primary or foreign key attributes (e.g., both have an "id" integer attribute representing the same entity type), treat these schemas as representing the same logical entity and include all such schemas in the output mapping. 
**IMPORTANT**:
- The parameter and schema attribute must either share the same data type or be of an array type.
- Semantic Constraint (Semantic Match): Map a parameter to a schema property only when they describe the same entity or fulfill the same logical purpose.
- Exclude Descriptive Attributes: Do not map parameters to descriptive or configuration-related schema properties — even if they share the same name
- Do not return nested attributes or dot notation (e.g., user.id).
- If a parameter corresponds to a key inside a referenced schema, map the parameter under that referenced schema instead.
- Each attribute must belong directly to the schema where it is declared.
- Additionally, when a schema contains nested or referenced schemas (e.g., arrays or objects within a schema), analyze those nested schemas as well to identify potential matching keys relevant to the endpoint parameters.
**Fallback Rule (Natural Key Substitution):**
- If no primary/foreign key exists, map to a natural key (e.g., name, code, key) only if it is from the same entity, has the same type, is likely unique, and is not descriptive (e.g., exclude description, title).
FINAL OUTPUT:
The response is in the format below, no explanation is needed:
```json {
  "schemas": {
    "schema_1": {
      "parameter_name_1::parameter": "attribute_name_1, attribute_name_2",
      "parameter_name_2::requestBody": "attribute_name_3, attribute_name_4"
    }
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
    response, _ = self.llm.generate(
      system_prompt=self.SYSTEM_PROMPT,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("OpSchemaDeps Response: " + response.model_dump_json(indent=2))
    return response.schemas
  
import json
from time import sleep
from api_testing.utils.log import getLogger

class ResponseConstraints:
  SYSTEM_PROMPT = """
You are given a schema and its attributes. Identify any constraints, rules, or limitations implied by each attribute’s description. Confirm that the description contains enough information to support automated validation of these constraints.
Follow these steps below to complete your task:
**STEP 1**: Review the provided schema and its attributes. Briefly describe the purpose or function of each attribute based on its definition or description.
**STEP 2**: From STEP 1, identify attributes whose name and descriptions imply constraints, rules, or limits that can be programmatically verified:
- Semantic inference: Constraints can be inferred from the attribute’s name and description based on their common or contextual meaning.
- General: Descriptions defining specific values, ranges, formats, or logic indicate constraints.
- Format: Mention or imply URI/URL, timestamp (ISO 8601), email, slug, date, datetime, version, or schema hints like format: uri, format: date-time.
- Enum: Fixed value sets (e.g., “one of public, private”).
- Range: Numeric or string limits (e.g., “≤255”, “1–10”, “max length 32”).
- Ignore vague terms: “recommended”, “typically”, “usually” are not constraints unless precise.
- Examples: Examples showing valid formats (URL, date, etc.) imply constraints if consistent.

FINAL OUTPUT:
The response is in the format below, no explanation is needed:
```json {
  "constraints": ["attribute_name_1","attribute_name_2"]
}```
"""
  PROMPT = """
Please review the following details for the schema and its attributes:
Schema: {schema}
Attributes:
{attributes}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)

  
  def exec(self, *args, **kargs):
    prompt = self.PROMPT.format(*args, **kargs) ## pass
    self.logger.debug("ResponseConstraints Prompt: " + prompt)
    for i in range(3):  # Thử lại tối đa 3 lần nếu không lấy được JSON hợp lệ
      try:
        response, _ = self.llm.generate(
          system_prompt=self.SYSTEM_PROMPT,
          prompt=prompt,
          # schema=Verdict
        )
        self.logger.debug("ResponseConstraints Response: " + response)
        
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
  
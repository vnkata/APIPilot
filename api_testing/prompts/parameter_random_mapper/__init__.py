import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class ParameterRandomMapper:
  SYSTEM_PROMPT = """
You are a system that determines the best matching data generator class for each input property.
The list below contains all generator classes and their corresponding descriptions:
{genFunction}
## IMPORTANT ## 
- If uncertain, or if properties have interdependent constraints, please fallback to LLMGenerator.
FINAL OUTPUT:
The response is in the format below, no explanation is needed:
{{
  "mapping": [
    {{
      "property": "...",
      "generator": {{
        "className": "...",
        "args": {{
          "arg1": "...",
          "arg2": "..."
        }}
      }}
    }}
  ]
}}
"""
  PROMPT = """
Please review the following details for each input property to identify the corresponding data generator class for it:
Here is list input property and descriptions:
{attributes}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)
  
  def exec(self, *args, **kargs):
    system = self.SYSTEM_PROMPT.format(genFunction=kargs.get("genFunction"))
    prompt = self.PROMPT.format(attributes=kargs.get("attributes")) ## pass
    self.logger.debug("ParameterRandomMapper Prompt: " + system)
    self.logger.debug("ParameterRandomMapper Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=system,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("ParameterRandomMapper Response: " + str(response))

    return response.mapping
  
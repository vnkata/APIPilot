import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class ParameterRandomMapper:
  SYSTEM_PROMPT = """
You are a system that determines the best matching data generator class for each input property.
The list below contains all generator classes and their corresponding descriptions:
{genFunction}
## IMPORTANT
* Select bestmaching data generator class and its `arguments` for each input property to ensure the generated data is logical, meaningful, and as realistic as possible.
* **Fallback to `LLMGenerator`:** Use it for complex or lengthy regex patterns, difficult constraints, or intricate string formats (e.g., currency, region).
* **Uncertain or dependent constraints:** Default to `LLMGenerator`.
* **Scope:** Apply fallback at the **field level**, not the entire object.
* **Data quality:** Ensure all generated values are valid, realistic, and comply with the given constraints.
FINAL OUTPUT:
The response is in the format below, no explanation is needed:
{{
  "mapping": [
    {{
      "idx": "...",
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
    response, _ = self.llm.generate(
      system_prompt=system,
      prompt=prompt,
      schema=Verdict
    )
    self.logger.debug("ParameterRandomMapper Response: " + response.model_dump_json())

    return response.mapping
  
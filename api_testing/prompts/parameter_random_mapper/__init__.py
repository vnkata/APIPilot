import json
from time import sleep
from .schema import Verdict
from api_testing.utils.log import getLogger

class ParameterRandomMapper:
  SYSTEM_PROMPT = """
You are a system that maps input parameters to the most suitable data generator classes.
Here is list class and descriptions:
{class_descriptions}
"""
  PROMPT = """
Please review the following details for parameters to identify the corresponding functions for it:
{parameters}
"""
  def __init__(self, llm):
    self.llm = llm
    self.logger = getLogger(__name__)
  
  def exec(self, *args, **kargs):
    system = self.SYSTEM_PROMPT.format(class_descriptions=kargs.get("class_description"))
    prompt = self.PROMPT.format(parameters=kargs.get("parameter_description")) ## pass
    self.logger.debug("ParameterRandomMapper Prompt: " + prompt)
    response, _ = self.llm.generate(
      system_prompt=system,
      prompt=prompt,
    )
    self.logger.debug("ParameterRandomMapper Response: " + response)
    return response.schemas
  
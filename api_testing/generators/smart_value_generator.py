from typing import Any, Dict, List, Optional

from api_testing.models.http_data import RequestData
from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties
from api_testing.prompts.smart_value_generate import SmartValueGenerate

class SmartValueGenerator:
  def __init__(self,operation: OperationProperties, parameters: Dict[str, ParameterProperties], request_body: Optional[ItemProperties] = None, model=None, no_requested=10):
    self.operation = operation
    self.parameters = parameters
    self.request_body = request_body
    self.model = model
    self.no_requested = no_requested
    self._generator = SmartValueGenerate(llm=model)
  
  def exec(self):
    params = {
      "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
      "summary": ((self.operation.summary or "") + " " + (self.operation.description or "")).strip(),
      "no_requested": self.no_requested,
      "specific_endpoint_params": "\n".join([
        f"- {k} : {v.to_human_readable()}"   
        for k, v in self.parameters.items() 
      ]),
      "specific_endpoint_body": None
    }
    if len(self.request_body) > 0:
      params["specific_endpoint_body"] = self.request_body.to_human_readable()
    results = self._generator.exec(**params)
    return results.datas

  

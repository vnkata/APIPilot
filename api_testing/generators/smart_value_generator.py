from dataclasses import asdict
from typing import Any, Dict, List, Optional

from api_testing.models.http_data import RequestData
from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties
from api_testing.prompts.smart_value_generate import SmartValueGenerate

class SmartValueGenerator:
  def __init__(self,operation: OperationProperties, parameters: Dict[str, ParameterProperties], request_body: Optional[ItemProperties] = None, model=None, num_test_cases=10, context_pool=None):
    self.operation = operation
    self.parameters = parameters
    self.request_body = request_body
    self.model = model
    self.num_test_cases = num_test_cases
    self._generator = SmartValueGenerate(llm=model)
    self.context_pool = context_pool
  
  def exec(self):
    params = {
      "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
      "summary": ((self.operation.summary or "") + " " + (self.operation.description or "")).strip(),
      "num_test_cases": self.num_test_cases,
      "specific_endpoint_params": "\n".join([
        f"- {k} : {v.to_human_readable()}"   
        for k, v in self.parameters.items() 
      ]),
      "specific_endpoint_body": None
    }
    if len(self.request_body) > 0:
      params["specific_endpoint_body"] = self.request_body.to_human_readable()
    results = self._generator.exec(**params)
    results = results.dict().get("datas")
    # 
    producer_parameters = { k: v for k,v in self.parameters.items() if v.strategy is not None and v.strategy.type == "ProducerGenerator"}
    for result in results:
      parameter = result.get("parameters")
      for k,_ in parameter.items():
        if k in producer_parameters:
          newVal = producer_parameters.get(k).generator.next_value(context_pool=self.context_pool)
          if newVal is not None:
            result[k] = newVal
    return results

  async def exec_async(self):
    params = {
      "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
      "summary": ((self.operation.summary or "") + " " + (self.operation.description or "")).strip(),
      "num_test_cases": self.num_test_cases,
      "specific_endpoint_params": "\n".join([
        f"- {k} : {v.to_human_readable()}"
        for k, v in self.parameters.items()
      ]),
      "specific_endpoint_body": None
    }
    if len(self.request_body) > 0:
      params["specific_endpoint_body"] = self.request_body.to_human_readable()
    results = await self._generator.a_exec(**params)
    results = results.dict().get("datas")
    #
    producer_parameters = { k: v for k,v in self.parameters.items() if v.strategy is not None and v.strategy.type == "ProducerGenerator"}
    for result in results:
      parameter = result.get("parameters")
      for k,_ in parameter.items():
        if k in producer_parameters:
          newVal = producer_parameters.get(k).generator.next_value(context_pool=self.context_pool)
          if newVal is not None:
            result[k] = newVal
    return results

  

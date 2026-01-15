import copy
from enum import Enum, auto
import random
from typing import Dict

from api_testing.generators.requestor import Requestor
from api_testing.generators.smart_value_generator import SmartValueGenerator
from api_testing.models.http_data import RequestData
from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties

class Strategy(Enum):
  SMART_VALUE = auto()      # dùng GPT hoặc logic nâng cao
  NAIVE_VALUE = auto()      # random đơn giản
  COUNTER_VALUE = auto()    # sinh giá trị đối nghịch / edge-case
  FUZZY_VALUE = auto() 
  # FIXED_VALUE = auto()      # giá trị cố định
  # CONTEXT_AWARE = auto()    # phụ thuộc context trước đó
  # SEMANTIC_MATCH = auto()   # dựa vào ngữ nghĩa parameter

class Executor:
  def __init__(self, api_url: str=None, strategy: Strategy = Strategy.SMART_VALUE, operation: OperationProperties = None, cache_dir=None,model=None ):
    self.api_url = api_url
    self.strategy = strategy
    self.operation = operation
    self.cache_dir = cache_dir
    self.model = model
    
  def generate_values(self):
    request = RequestData(
      endpoint_path=self.operation.endpoint_path,
      http_method=self.operation.http_method,
      mime_type=random.choice(self.operation.request_body.keys()) if len(self.operation.request_body) > 0 else "application/json",
    )
    parameters = self.operation.parameters
    request_body = self.operation.request_body[request.mime_type] if len(self.operation.request_body) > 0 else {}
    match (self.strategy): 
      case Strategy.SMART_VALUE:
        values = self.generate_smart_values(self.operation, parameters, request_body)
        data = []
        for val in values:
          newReq = copy.copy(request)
          newReq.parameters = val.parameters
          newReq.request_body = val.requestBody
          data.append(newReq)
        return data                
      case Strategy.NAIVE_VALUE:
        pass
    return request
      # case Strategy.COUNTER_VALUE:
			# 	pass
  
  def generate_smart_values(self,operation: OperationProperties, parameters: Dict[str, ParameterProperties], request_body: Dict[str, ItemProperties]):
    """
    Generate smart values for parameters and request body using LLMs
    :param operation_properties: Dictionary mapping of operation properties
    :param requirements: RequestRequirements object that contains any parameters or request body requirements
    :return: a tuple of the generated parameters and request body
    """
    value_generator = SmartValueGenerator(operation, parameters=parameters, request_body=request_body, model=self.model)
    return value_generator.exec()
  
  def exec(self):
    data = self.generate_values()
    requestor = Requestor(api_url=self.api_url, cache_dir=self.cache_dir)
    for item in data:
      requestor.exec(request_data=item)
import copy
from dataclasses import asdict, field, fields, replace
from enum import Enum, auto
import random
from typing import Any, Dict

from api_testing.generators.naive_value_generator import NaiveValueGenerator
from api_testing.generators.requestor import Requestor
from api_testing.generators.smart_value_generator import SmartValueGenerator
from api_testing.models.generator_model import ParameterGenerator
from api_testing.models.http_data import RequestData
from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties

class Strategy(Enum):
  SMART_VALUE = auto()      # use GPT
  NAIVE_VALUE = auto()      # combine params
  COUNTER_VALUE = auto()    # sinh giá trị đối nghịch / edge-case
  FUZZY_VALUE = auto()      # sinh data fuzzy

class Executor:
  def __init__(self, api_url: str=None, strategy: Strategy = Strategy.SMART_VALUE, operation: OperationProperties = None, cache_dir=None,model=None,configuration=None,
               num_test_cases=1, context_pool=None):
    self.api_url = api_url
    self.strategy = strategy
    self.operation = operation
    self.cache_dir = cache_dir
    self.model = model
    self.configuration = configuration
    self.sender = Requestor(api_url=self.api_url, cache_dir=self.cache_dir)
    self.context_pool = context_pool
    self.num_test_cases = num_test_cases

  def generate_values(self):
      req_body = self.operation.request_body
      mime = random.choice(list(req_body.keys())) if req_body else "application/json"
      
      base_request = RequestData(
          endpoint_path=self.operation.endpoint_path,
          http_method=self.operation.http_method,
          mime_type=mime,
          headers={
             "PRIVATE-TOKEN": "zmy1FupqQvgL9BgG1sqw"
          }
      )

      params = self.operation.parameters
      body_schema = req_body.get(mime, {})

      def build_requests(values):
        return [
						replace(base_request,
										parameters=v.get("parameters"),
                                        expected_code=v.get("expected_code"),
										body=getattr(v, "requestBody", None))
						for v in values
				]
      def merge_config(p: ParameterProperties | ItemProperties = None, 
                      conf: Dict[str, 'FieldConfiguration'] = None):
          # 1. Trả về None nếu đầu vào trống
          if p is None:
              return None
          # 2. Nếu là ItemProperties (thường là list các item), trả về nguyên bản 
          # hoặc xử lý theo logic riêng của bạn
          if isinstance(p, ItemProperties):
              return p
          # Giả định conf mặc định là dict trống nếu không truyền vào
          conf = conf or {}
          result = {}
          # 3. Duyệt qua dictionary của ParameterProperties
          for k, v in p.items():
              # Chuyển v (BaseModel) thành dict
              param_data = v.to_dict() # Dùng .dict() nếu là Pydantic V1
              # Tạo generator từ dict
              generator = ParameterGenerator.from_dict(param_data)
              # Gán strategy từ config nếu tồn tại
              if k in conf:
                  generator.strategy = conf[k] 
              result[k] = generator
              
          return result
      match self.strategy:
          case Strategy.SMART_VALUE:
              params = merge_config(params, self.configuration.params)
              body_schema = merge_config(body_schema, self.configuration.request_body)
              values = self.generate_smart_values(self.operation, params, body_schema)
              return build_requests(values)

          case Strategy.NAIVE_VALUE:
              params = merge_config(params, self.configuration.params)
              body_schema = merge_config(body_schema, self.configuration.request_body)
              values = self.generate_naive_values(self.operation, params, body_schema)
              return build_requests(values)

          case Strategy.COUNTER_VALUE | Strategy.FUZZY_VALUE:
              # TODO: implement later (read config, merge, etc.)
              return []

          case _:
              raise NotImplementedError("Strategy not implemented")

      return []
  
  def generate_smart_values(self,operation: OperationProperties, parameters: Dict[str, ParameterProperties], request_body: Dict[str, ItemProperties]):
    """
    Generate smart values for parameters and request body using LLMs
    :param operation_properties: Dictionary mapping of operation properties
    :param requirements: RequestRequirements object that contains any parameters or request body requirements
    :return: a tuple of the generated parameters and request body
    """
    value_generator = SmartValueGenerator(operation, parameters=parameters, request_body=request_body, model=self.model, num_test_cases=self.num_test_cases, context_pool = self.context_pool)
    return value_generator.exec()
  
  def generate_naive_values(self,operation: OperationProperties, parameters: Dict[str, ParameterProperties], request_body: Dict[str, ItemProperties]):
    value_generator = NaiveValueGenerator(operation, parameters=parameters, request_body=request_body, model=self.model, num_test_cases=self.num_test_cases, context_pool = self.context_pool, cache_dir=self.cache_dir)
    return value_generator.exec()
  
  def exec(self):
    data = self.generate_values()
    for item in data:
      self.sender.exec(request_data=item)
    return self.sender.entries
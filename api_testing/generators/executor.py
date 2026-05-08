import copy
from dataclasses import asdict, field, fields, replace
from enum import Enum, auto
import random
from typing import Any, Dict

from api_testing.generators.naive_value_generator import NaiveValueGenerator
from api_testing.generators.requestor import Requestor
from api_testing.generators.smart_value_generator import SmartValueGenerator
from api_testing.models.generator_model import ItemGenerator, ParameterGenerator
from api_testing.models.http_data import RequestData
from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties
from api_testing.utils import flatten_item_properties, get_required_body_params
from fake_useragent import UserAgent
import time

class Strategy(Enum):
  SMART_VALUE = auto()      # use GPT
  NAIVE_VALUE = auto()      # combine params
  COUNTER_VALUE = auto()    # sinh giá trị đối nghịch / edge-case
  FUZZY_VALUE = auto()      # sinh data fuzzy

def merge_config(
        p: ParameterProperties | ItemProperties | Dict[str, Any] = None,
        conf: Dict[str, "FieldConfiguration"] = None,
    ):
        if p is None:
            return None

        conf = conf or {}

        # -------------------------
        # CASE 1: Request Body (ItemProperties)
        # -------------------------
        if isinstance(p, ItemProperties):
            schema_type = getattr(p, "type", None)
            # 🔥 ARRAY
            if schema_type == "array":
                item_schema = getattr(p, "items", None)

                generator = ItemGenerator.from_dict(p.to_dict())

                # apply config (áp dụng cho whole array nếu có key đặc biệt)
                if "__self__" in conf:
                    generator.strategy = conf["__self__"]
                return {
                    "__type__": "array",
                    "__generator__": generator,
                    "description": p.description,
                    "items": merge_config(item_schema, conf),
                }
            # 🔥 OBJECT
            elif schema_type == "object" or getattr(p, "properties", None) is not None:
                result = {}
                flatten_items = flatten_item_properties(p)
                required = get_required_body_params(p)
                for k, v in flatten_items.items():
                    param_data = v.to_dict()
                    generator = ItemGenerator.from_dict(param_data)
                    # required → nullable = False
                    if k in required:
                        generator.nullable = False

                    # apply config
                    if k in conf:
                        generator.strategy = conf[k]

                    result[k] = generator

                return {
                    "__type__": "object",
                    "properties": result,
                }

            # 🔥 PRIMITIVE
            else:
                generator = ItemGenerator.from_dict(p.to_dict())

                if "__self__" in conf:
                    generator.strategy = conf["__self__"]

                return {
                    "__type__": "primitive",
                    "__generator__": generator,
                }

        # -------------------------
        # CASE 2: Parameters (dict)
        # -------------------------
        result = {}
        for k, v in p.items():
            param_data = v.to_dict()
            generator = ParameterGenerator.from_dict(param_data)

            if k in conf:
                generator.strategy = conf[k]

            result[k] = generator

        return result


class Executor:
  def __init__(self, api_url: str=None, strategy: Strategy = Strategy.SMART_VALUE, operation: OperationProperties = None, cache_dir=None,model=None,configuration=None,
               num_test_cases=1, context_pool=None, mutation_ratio = 0.1):
    self.api_url = api_url
    self.strategy = strategy
    self.operation = operation
    self.cache_dir = cache_dir
    self.model = model
    self.configuration = configuration
    self.sender = Requestor(api_url=self.api_url, cache_dir=self.cache_dir)
    self.context_pool = context_pool
    self.num_test_cases = num_test_cases
    self.mutation_ratio = mutation_ratio

  def mutator(self, requests: list["RequestData"], body_schema) -> list["RequestData"]:
    if not requests:
        return []

    mutated = []
    operation_mimetypes = set(self.operation.minetypes or [])

    # Một số MIME sai phổ biến để induce 4xx
    invalid_mimes = [
        "application/xml",
        "text/plain",
        "multipart/form-data",
        "application/x-www-form-urlencoded",
        "application/invalid"
    ]
    ua = UserAgent()
    # covert_to_array = body_schema and isinstance(body_schema, ItemProperties) and (body_schema.type == "array" or body_schema.items) 
    for req in requests:
        # chỉ mutate một phần theo ratio + chỉ khi expected 4xx
        if req.expected_code == "4xx":
            new_mime = req.mime_type
            if random.random() < self.mutation_ratio:
                # chọn mime sai (không nằm trong operation)
                candidate_mimes = list(set(invalid_mimes) - operation_mimetypes)
                if not candidate_mimes:
                    candidate_mimes = invalid_mimes  # fallback
                new_mime = random.choice(candidate_mimes)
            new_headers = {}
            if random.random() < self.mutation_ratio:                
                new_headers = { "User-Agent": ua.random }
            http_method = req.http_method
            if random.random() < 0.4:  # 40% chance to mutate HTTP method
                # chọn mime sai (không nằm trong operation)
                candidate_mimes = list(set(["DELETE","GET","POST", "PUT", "PATCH", "OPTIONS", "HEAD", "TRACE"]) - set([req.http_method]))
                http_method = random.choice(candidate_mimes)
            
            mutated_req = replace(
                req,
                http_method=http_method,
                mime_type=new_mime,
                headers={**req.headers, "Content-Type": new_mime, **new_headers}
            )

            mutated.append(mutated_req)
        else:       
            mutated.append(req)

    return mutated
     
  def generate_values(self):
      req_body = self.operation.request_body
      operation_mimetypes = self.operation.minetypes

      if req_body:
          mime = random.choice(list(req_body.keys()))
      elif operation_mimetypes:
          mime = random.choice(operation_mimetypes)
      else:
          mime = "application/json"
      headers = {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Accept": "*/*"
      }

      # 2. Cập nhật Content-Type dựa trên mime (giả sử 'mime' là biến chứa type)
      if mime == "application/octet-stream":
        headers["Content-Type"] = "application/octet-stream"
      base_request = RequestData(
          uuid=self.operation.uuid,
          endpoint_path=self.operation.endpoint_path,
          http_method=self.operation.http_method,
          mime_type=mime,
          headers=headers
      )

      params = self.operation.parameters
      body_schema = req_body.get(mime, {})
      
      def build_requests(values):
        return [
						replace(base_request,
										parameters=v.get("parameters"),
                                        expected_code=v.get("expected_code"),
										body=v.get("requestBody"))
						for v in values
				]
      
    
      match self.strategy:
          case Strategy.SMART_VALUE:
              params = merge_config(params, self.configuration.params)
              body_schema = merge_config(body_schema, self.configuration.request_body)
              values = self.generate_smart_values(self.operation, params, body_schema)
              values = build_requests(values)
              return self.mutator(values, req_body.get(mime, {}))

          case Strategy.NAIVE_VALUE:
              params = merge_config(params, self.configuration.params)
              body_schema = merge_config(body_schema, self.configuration.request_body)
              values = self.generate_naive_values(self.operation, params, body_schema)
              values = build_requests(values)
              return self.mutator(values, req_body.get(mime, {}))
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
    value_generator = SmartValueGenerator(operation, parameters=parameters, request_body=request_body, model=self.model, num_test_cases=self.num_test_cases, context_pool = self.context_pool, mutation_ratio = self.mutation_ratio)
    return value_generator.exec()
  
  def generate_naive_values(self,operation: OperationProperties, parameters: Dict[str, ParameterProperties], request_body: Dict[str, ItemProperties]):
    value_generator = NaiveValueGenerator(operation, parameters=parameters, request_body=request_body, model=self.model, num_test_cases=self.num_test_cases, context_pool = self.context_pool, cache_dir=self.cache_dir,  mutation_ratio = self.mutation_ratio)
    return value_generator.exec()
  
  def exec(self):
    data = self.generate_values()
    for item in data:
    #   print("HTTP Request", asdict(item))
      self.sender.exec(request_data=item)
    return self.sender.entries
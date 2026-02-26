import hashlib
import json
import os
import random
from typing import Dict, List, Optional, Set, Tuple

from api_testing.models.specification_model import ItemProperties
from api_testing.utils import get_combinations
from api_testing.utils.common import remove_nulls


class NaiveValueGenerator:
  def __init__(self, operation: 'OperationProperties', parameters: Dict[str, 'ParameterProperties'], request_body: Dict[str, 'ItemProperties'], model=None, num_test_cases=1,  cache_dir: str = ".", context_pool=None):
    self.operation = operation
    self.parameters = parameters
    self.request_body = request_body
    self.model = model
    self.num_test_cases = num_test_cases
    self.cache_dir = cache_dir
    self.context_pool = context_pool

  def __get_combination_parameters(self, parameters):
    key = hashlib.md5(json.dumps({"endpoint": self.operation.uuid, "params": list(parameters.keys())}, sort_keys=True).encode()).hexdigest()
    
    CACHE_FILE = os.path.join(self.cache_dir, key) + ".json"
    if os.path.exists(CACHE_FILE):
      try:
          with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
      except json.JSONDecodeError:
          cache = []
      return cache
    else:
      parameter_label = self.parameters.keys()
      parameter_required_label = { k for k, v in self.parameters.items() if v.required}
      params_combinations = get_combinations(parameter_label, parameter_required_label)
      with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(params_combinations, f, indent=2, ensure_ascii=False)
      return params_combinations
    
  def __get_combination_request_body__(self, request_body):
    def get_body_combinations(
        operation_body: Dict[str, ItemProperties],
    ) -> Dict[str, List[Tuple[str]]]:
        return {
            k: get_combinations(v)
            for k, v in get_request_body_params(operation_body).items()
        }
    
    def get_body_params(body: ItemProperties) -> List[str]:
        if body is None:
            return []

        elif body.properties and body.type == "object":
            body_params = []
            for key, value in body.properties.items():
                body_params.append(key)
            return body_params

        elif body.items and body.type == "array":
            return get_body_params(body.items)

        return []

    def get_request_body_params(
        operation_body: Dict[str, ItemProperties],
    ) -> Dict[str, List[str]]:
        return (
            {k: get_body_params(v) for k, v in operation_body.items()}
            if operation_body is not None
            else {}
        )
    
    def get_body_object_combinations(
        body_schema: ItemProperties,
        required_body_params: Optional[Set[str]] = None,
        seed: Optional[str] = None,
    ) -> List[Tuple[str, ...]]:
        return get_combinations(
            get_body_params(body_schema), required=required_body_params, seed=seed
        )
  def exec(self):
    # process parameters
    params_combinations = self.__get_combination_parameters(self.parameters)
    data = [] 
    required_parameters = [param for param, props in self.parameters.items() if props.required]
    default = False
    for _ in range(self.num_test_cases):
        params = random.choice(params_combinations)
        if not default:
            default = True
            params = required_parameters
        else:
            params = list(params) + required_parameters
  
        params = list(set(params))
  
        generated_dict = {}
        for param_name in params:
            # 1. Sinh giá trị gốc từ generator
            val = self.parameters.get(param_name).generator.next_value(context_pool=self.context_pool)
  
            # 2. Áp dụng mutation nếu thỏa mãn tỉ lệ
            if random.random() < self.mutation_ratio:
                val = self.parameters.get(param_name).generator.next_fuzz_value(strategy=self.context_pool)
  
  
            generated_dict[param_name] = val
        data.append({
            "parameters": remove_nulls(generated_dict), 
            "expected_code": "2xx"
        })
        self.context_pool.clear_cache()
  
    return data

#   def exec(self):
#     # process parameters
#     params_combinations = self.__get_combination_parameters(self.parameters) #
#     data = [] 
#     required_parameters = [ param for param, props in self.parameters.items() if props.required]
#     default = False
#     for _ in range(self.num_test_cases):
#       params = random.choice(params_combinations) ## merge with defaults
#       if not default:
#         default = True
#         params = required_parameters
#       else:
#         params = list(params) + required_parameters
#       params = list(set(params))
#       dict = remove_nulls({ param: self.parameters.get(param).generator.next_value(context_pool=self.context_pool) for param in params})
#       data.append({"parameters": dict, "expected_code": "2xx"})
#       self.context_pool.clear_cache()
#     return data
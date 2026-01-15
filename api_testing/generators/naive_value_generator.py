from typing import Dict


class NaiveValueGenerator:
    def __init__(self, parameters: Dict[str, 'ParameterProperties'], request_body: Dict[str, 'ItemProperties'], model=None):
      self.parameters = parameters
      self.request_body = request_body
      self.model = model
      

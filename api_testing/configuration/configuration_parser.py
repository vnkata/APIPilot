from api_testing.inputs import RandomGeneratorFactory
from api_testing.inputs.random.random_number_generator import DataType
from api_testing.models.configuration_model import FieldConfiguration
from api_testing.models.specification_model import ParameterProperties
from api_testing.prompts.parameter_random_mapper import ParameterRandomMapper


class ConfigurationParser:
    def __init__(self, spec_parser=None, model=None):
      self.spec_parser = spec_parser
      self.model = model
      self.parameter_random_mapper = ParameterRandomMapper(llm=self.model)
    
    def parse(self):
        operations = self.spec_parser.operations
        for operation in operations.values():
            parser = {
                "parameters": {}   
            }    
            for param_name, param_details in operation.parameters.items():
                if param_details.description is None:
                    parser["parameters"][param_name] = self.heuristic_parser(param_details)
                else:
                    parser["parameters"][param_name] = self.gpt_parser(param_details)

    def gpt_parser(self, parameter: ParameterProperties):
        factory = RandomGeneratorFactory()
        descriptions = factory.gen_description()
        params = {
            "class_description": "/n".join([f"- {k}: {v}" for k, v in factory.gen_description().items()]),
            "parameter_description": f"{parameter.name}: {parameter.to_human_readable()}" 
        }
        print(params)
        results = self.parameter_random_mapper.exec(**params)
        print(results)

        print(descriptions)
        
    def heuristic_parser(self, parameter: ParameterProperties ):
        
        match parameter.schema.type:
            case "boolean":
                return FieldConfiguration(name=parameter.name, type="RandomBooleanGenerator")
            case "number":
                return FieldConfiguration(name=parameter.name, type="RandomBooleanGenerator")
            case "integer":
                params = {
                    "name": parameter.name, 
                    "type": "RandomNumberGenerator"
                }
                schema = parameter.schema
                if schema.minimum is not None:
                    params["minimum"] = schema.minimum
                if schema.maximum is not None:
                    params["maximum"] = schema.maximum
                if schema.format is not None:
                    match schema.format:
                        case 'int32':
                            params["type"] = DataType.INT32
                        case 'int64':
                            params["type"] = DataType.INT64
                        case 'unix-time':
                            params["type"] = DataType.INT64 # unknow will fix in future

                return FieldConfiguration(**params)
            case "string":
                params = {
                    "name": parameter.name, 
                    "type": "RandomNumberGenerator"
                }
                schema = parameter.schema
                if schema.minimum is not None:
                    params["minimum"] = schema.minimum
                if schema.maximum is not None:
                    params["maximum"] = schema.maximum
                return FieldConfiguration(**params)

            


import json

import os
from pathlib import Path
from .prance import ResolvingParser
import json
from typing import List, Dict, Optional, Union, Iterable

from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties, ResponseProperties
from api_testing.utils import to_dict_helper


def recursion_limit_handler_none(limit, refstring, recursions):
    return {}

class SpecificationParser:
    """
    Class to parse a specification file and return a dictionary of all the operations and their properties.
    """

    def __init__(self, spec_path=None, recursion_limit=1):
        self.spec_path = spec_path
        if spec_path is not None:
            self.resolving_parser = ResolvingParser(
                spec_path,
                strict=False,
                recursion_limit=recursion_limit,
                recursion_limit_handler=recursion_limit_handler_none,
            )
        self.operations = {}
        self.schemas = {}
    # load specification from file

    def get_api_url(self) -> str:
        """
        Extract the server URL from the specification file.
        """
        return self.resolving_parser.specification.get('servers', {}).get("0", {}).get('url', None)

    def get_api_title(self) -> str:
        """
        Extract the title of the API from the specification file.
        """
        return self.resolving_parser.specification.get('info', {}).get('title')

    def load_from_file(self, spec_cache):
        operation_collection = {}
        with open(spec_cache, "r",encoding="utf-8") as file:
            data = json.load(file)
            for operation_id, operationProperties in data.get("operations").items():
                operation_properties = OperationProperties.from_dict(
                    operationProperties)
                operation_collection.setdefault(
                    operation_id, operation_properties)
        self.operations = operation_collection
        return operation_collection

    def load_or_initialize(self, cache_dir=None):
        # Check if the cache file exists
        self.cache_file = os.path.join(cache_dir, "specification.json")
        if os.path.exists(self.cache_file):
            print(f"Loading openapi from cache: {self.cache_file}")
            self.load_from_file(self.cache_file)
        else:
            print("Cache file not found. Initializing Specification...")
            self.parse_specification()
            self.json_spec_output(file_name=self.cache_file)
        # # save to cache

    def process_parameter_object_properties(self, properties: Dict) -> Dict[str, ItemProperties]:
        """
        Process the properties of a parameter of type object to return a dictionary of all the properties and their
        corresponding parameter values.
        """
        if properties is None:
            return None

        object_properties = {}
        for name, values in properties.items():
            # check if this is correct, or if it should be process_parameter
            object_properties.setdefault(
                name, self.process_parameter_schema(values))
        return object_properties

    def process_parameter_schema(self, schema: Dict) -> ItemProperties:
        """
        Process the schema of a parameter to return a ValueProperties object
        """
        if not schema:
            return None

        value_properties = ItemProperties(
            type=schema.get('type'),
            format=schema.get('format'),
            description=schema.get('description'),
            items=self.process_parameter_schema(
                schema.get('items')),  # recursively process items
            properties=self.process_parameter_object_properties(
                schema.get('properties')),
            required=schema.get('required'),
            default=schema.get('default'),
            enum=schema.get('enum'),
            minimum=schema.get('minimum'),
            maximum=schema.get('maximum'),
            min_length=schema.get('minLength'),
            max_length=schema.get('maxLength'),
            pattern=schema.get('pattern'),
            max_items=schema.get('maxItems'),
            min_items=schema.get('minItems'),
            unique_items=schema.get('uniqueItems'),
            additional_properties=schema.get('additionalProperties'),
            nullable=schema.get('nullable'),
            read_only=schema.get('readOnly'),
            write_only=schema.get('writeOnly'),
            example=schema.get('example'),
            examples=schema.get('examples'),
            xrefs=schema.get('x-refs')
        )
        return value_properties

    def process_parameter(self, parameter) -> ParameterProperties:
        """
        Process an individual parameter to return a ParameterProperties object.
        """
        parameter_properties = ParameterProperties(
            name=parameter.get('name'),
            in_value=parameter.get('in'),
            description=parameter.get('description'),
            required=parameter.get('required'),
            deprecated=parameter.get('deprecated'),
            allow_empty_value=parameter.get('allowEmptyValue'),
            style=parameter.get('style'),
            explode=parameter.get('explode'),
            allow_reserved=parameter.get('allowReserved')
        )
        if parameter.get('schema'):
            parameter_properties.schema = self.process_parameter_schema(
                parameter.get('schema'))
        
        return parameter_properties

    def process_parameters(self, parameter_list) -> Dict[str, ParameterProperties]:
        """
        Process the parameters list to return a Dictionary with all its properties and values.
        """
        parameters = {}
        if parameter_list:
            for parameter in parameter_list:
                parameter_properties = self.process_parameter(parameter)
                parameters.setdefault(
                    parameter_properties.name, parameter_properties)
        return parameters

    def process_request_body(self, request_body) -> Dict[str, ItemProperties]:
        """
        Process the request body to return a Dictionary with mime type and its properties and values.
        """

        request_body_properties = {}
        content = request_body.get('content')
        if content:
            for mime_type, mime_details in content.items():
                # if we need to check required list, do it here
                schema = mime_details.get('schema')
                if schema:
                    request_body_properties[mime_type] = self.process_parameter_schema(
                        schema)

        return request_body_properties

    def process_responses(self, responses) -> Dict[str, ResponseProperties]:
        """
        Process the responses to return a Dictionary with status code and its properties and values.
        """
        response_properties = {}
        for status_code, response_details in responses.items():
            response_properties.setdefault(status_code, ResponseProperties(
                status_code=status_code,
                description=response_details.get('description')
            ))
            content = response_details.get('content')
            if content:
                for mime_type, mime_details in content.items():
                    # if we need to check required list, do it here
                    schema = mime_details.get('schema')
                    if schema:
                        response_properties[status_code].content[mime_type] = self.process_parameter_schema(
                            schema)
        return response_properties

    def process_operation_details(self, http_method: str, endpoint_path: str, global_parameters: List, operation_details: Dict, external_docs: Dict) -> OperationProperties:
        """
        Process the parameters and request body details within a given operation to return as OperationProperties object.
        """
        operation_properties = OperationProperties(
            uuid=f'{http_method}-{endpoint_path}',
            operation_id=operation_details.get('operationId'),
            endpoint_path=endpoint_path,
            http_method=http_method,
            summary=operation_details.get('summary'),
            tags=operation_details.get('tags'),
            description=operation_details.get('description'),
            external_docs=operation_details.get(
                'external_docs') or external_docs
        )

        if operation_details.get("parameters"):
            operation_properties.parameters = self.process_parameters(
                parameter_list=global_parameters + operation_details.get('parameters'))

        if operation_details.get('requestBody'):
            operation_properties.request_body = self.process_request_body(
                request_body=operation_details.get('requestBody'))
        
        if operation_details.get('responses'):
            operation_properties.responses = self.process_responses(
                responses=operation_details.get('responses'))
        return operation_properties

    def parse_specification(self) -> Dict[str, OperationProperties]:
        """
        Parse the specification file to return a dictionary of all the operations and their properties.

        The key of the dictionary is the operationId and the value is an OperationProperties object.
        """
        supported_methods = ("get", "post", "put", "delete",
                             "head", "options", "patch")
        operation_collection = {}
        # global external docs
        external_docs = self.resolving_parser.specification.get(
            'externalDocs', None)
        self.schemas = self.resolving_parser.specification.get('components', {}).get('schemas', {}) # store schemas
        # process schema name
        spec_paths = self.resolving_parser.specification.get('paths', {})
        for endpoint_path, endpoint_details in spec_paths.items():
            global_parameters = endpoint_details.get("parameters", [])
            for http_method, operation_details in endpoint_details.items():
                if http_method in supported_methods:
                    operation_properties = self.process_operation_details(
                        http_method, endpoint_path, global_parameters, operation_details, external_docs)
                    operation_collection.setdefault(
                        operation_properties.uuid, operation_properties)
        self.operations = operation_collection ## assign to global 
        return operation_collection

    def json_spec_output(self, file_name: str):
        """
        Create a testing JSON file from the specification parsing output.
        """
        serializable_spec = to_dict_helper(self.operations)
        dicts = {
            "operations": serializable_spec,
        }
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(dicts, file, ensure_ascii=False, indent=4) 

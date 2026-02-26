

import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field, fields
from api_testing.utils import flatten_json_schema, to_dict_helper
from api_testing.utils.common import isEmpty, remove_nulls
from api_testing.utils.http import isSuccessful

@dataclass
class ItemProperties:
    """
    Class to store the properties of either the schema values, in the case of parameters, or the request body object values
    """
    type: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None
    items: 'ItemProperties' = None
    properties: Dict[str, 'ItemProperties'] = None
    required: List[str] = field(default_factory=list)
    default: Optional[Union[str, int, float, bool, List, Dict]] = None
    enum: Optional[List[str]] = field(default_factory=list)
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    max_items: Optional[int] = None
    min_items: Optional[int] = None
    unique_items: Optional[bool] = None
    additional_properties: Union[bool, 'ItemProperties', None] = None
    nullable: Optional[bool] = None
    read_only: Optional[bool] = None
    write_only: Optional[bool] = None
    example: Optional[Union[str, int, float, bool, List, Dict]] = None
    examples: List[Optional[Union[str, int, float, bool, List, Dict]]] = field(
        default_factory=list)
    xrefs: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        if data is None:
            return data
        it = cls(**data)
        if data.get("items"):
            it.items = ItemProperties.from_dict(data.get("items"))
        if data.get("properties"):
            it.properties = {}
            for key, value in data.get("properties").items():
                it.properties[key] = ItemProperties.from_dict(value)
        return it

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    def to_human_readable(self,ingore_type=False):
        if self.type not in ('array', 'object'):
            # pass
            str = ''
            if ingore_type:
                str+= f'a attribute to describe {self.description}' if self.description else ' a attribute'
            else:
                str += f'a {self.type} to describe {self.description}' if self.description else f'a {self.type}'
            if self.format:
                str += f', format {self.format}'
            if self.pattern:
                str += f', pattern: {self.pattern}'
            if self.enum:
                str += f', values in of {self.enum}'
            if self.default:
                str += f', default: {self.default}'
            if self.minimum is not None:
                str += f', minimum: {self.minimum}'
            if self.maximum is not None:
                str += f', maximum: {self.maximum}'
            if self.min_length is not None:
                str += f', minimum length {self.min_length}'
            if self.max_length is not None:
                str += f', maximum length {self.max_length}'
            if self.min_items is not None:
                str += f' , minimum items {self.min_items}'
            if self.max_items is not None:
                str += f', maximum items {self.max_items}'
            if self.unique_items == True:
                str += f', array unique items' 
            if self.example:
                str += f', eg: {self.example}'
            return str

        if self.type == 'object':
            dict_items = {k: v.to_human_readable()
                          for k, v in self.properties.items() if v}
            if self.xrefs is not None:
                return f'a {self.xrefs} object'
                # return f'a {self.xrefs} object with schema ' + json.dumps(dict_items, indent=4)
            return json.dumps(dict_items, indent=4)
        if self.type == 'array':
            if not self.items:
                return ''
            dict_items = self.items.to_human_readable()
            if self.xrefs is not None:
                return f'a array of {self.xrefs} object'
                # return f'a array of {self.xrefs} object with schema ' + json.dumps(dict_items, indent=4)
            return dict_items
        return ''

@dataclass
class ParameterProperties:
    """
    Class to store the properties of a parameter. Parameters have nested schemas, whereas request bodies do not.
    """
    name: str = ''
    in_value: Optional[str] = None
    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    allow_empty_value: Optional[bool] = None
    style: Optional[str] = None
    explode: Optional[bool] = None
    allow_reserved: Optional[bool] = None
    schema: ItemProperties = None
    example: Optional[Union[str, int, float, bool, List, Dict]] = None
    examples: List[Optional[Union[str, int, float, bool, List, Dict]]] = field(
        default_factory=list)

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    @classmethod
    def from_dict(cls, data: dict):
        it = cls(**data)
        if data.get("schema"):
            it.schema = ItemProperties.from_dict(data.get("schema"))
        return it

    def to_human_readable(self):
        str = ''
        str += f'a {self.schema.type} to describe {self.description}' if self.description else f'a {self.schema.type} '
        #
        if self.schema.format:
            str += f', format {self.schema.format}'
        if self.schema.pattern:
            str += f', pattern: {self.schema.pattern}'

        if self.schema.enum:
            str += f', values in of {self.schema.enum}'

        if self.schema.default:
            str += f', default: {self.schema.default}'
        if self.schema.minimum is not None:
            str += f', minimum: {self.schema.minimum}'
        if self.schema.maximum is not None:
            str += f', maximum: {self.schema.maximum}'

        if self.schema.min_length is not None:
            str += f', minimum length {self.schema.min_length}'
        if self.schema.max_length is not None:
            str += f', maximum length {self.schema.max_length}'
        if self.schema.min_items is not None:
            str += f', minimum items {self.schema.min_items}'
        if self.schema.max_items is not None:
            str += f', maximum items {self.schema.max_items}'
        if self.schema.unique_items == True:
            str += f', array unique items'
        if self.schema.example:
            str += f', eg: {self.schema.example}'
        return str

    def __str__(self):
        return f"Parameter(name={self.name}, in_value={self.in_value}, required={self.required}, schema={self.schema})"


@dataclass
class ResponseProperties:
    """
    Class to store the properties of a response
    """
    status_code: int = -1
    description: Optional[str] = None
    # MIME type as first key, then schema content as result
    content: Dict[str, 'ItemProperties'] = field(default_factory=dict)

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    @classmethod
    def from_dict(cls, data: dict):
        it = cls(**data)
        if data.get("content"):
            for contentType, props in data.get("content").items():
                it.content[contentType] = ItemProperties.from_dict(props)
        return it

    # to human readable status 2xx

    def to_human_readable(self):
        if self.content:
            for content_type, properties in self.content.items():  # get first content type
                return properties.to_human_readable()
        return ''


@dataclass
class OperationProperties:
    """
    Class to store the properties of an operation, considering both its parameters and potential request body.
    """
    uuid: str = '',
    operation_id: str = ''
    endpoint_path: str = ''
    http_method: str = ''
    parameters: Dict[str, ParameterProperties] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    # if None then global document is apply
    external_docs: Dict[str, str] = None
    # MIME type as first key, then each parameter with its properties as second dict
    request_body: Dict[str, ItemProperties] = field(default_factory=dict)
    # status code as first key, then each response with its properties as second dict
    responses: Dict[str, ResponseProperties] = None

    # @property
    # def degree(self) -> int:
    #     # type: ignore
    #     return len(self.required_parameters)
    @property
    def schemas(self) -> Dict[str, ItemProperties]:
        
        def get_relevant_schema_of_endpoint(response: ResponseProperties) -> List[str]:
            relevant_schemas = {}

            def get_schema_recursive(item_properties: ItemProperties):
                if item_properties is None:
                    return
                if item_properties.xrefs and item_properties.type in ['object', 'array']:
                    schema_name = item_properties.xrefs
                    if schema_name not in relevant_schemas:
                        relevant_schemas[schema_name] = item_properties

                if item_properties.items:
                    get_schema_recursive(item_properties.items)
                if item_properties.properties:
                    for prop in item_properties.properties.values():
                        get_schema_recursive(prop)

            for status_code, properties in response.items():
                if isSuccessful(status_code):
                    for item_properties in properties.content.values():
                        get_schema_recursive(item_properties)
            return relevant_schemas

        return get_relevant_schema_of_endpoint(self.responses)

    @property
    def required_parameters(self) -> Dict[str, ParameterProperties]:
        # type: ignore
        return {k: v for k, v in self.parameters.items() if v.required}

    @property
    def optional_parameters(self) -> Dict[str, ParameterProperties]:
        return {k: v for k, v in self.parameters.items() if not v.required}
    
    @property
    def successful_responses(self) -> ItemProperties:
        if self.responses is None:
            return None
        for status_code, response_properties in self.responses.items():
            if status_code and isSuccessful(status_code) and response_properties.content:
                for _, response_details in response_properties.content.items():
                    return response_details
        return None
    
    @classmethod
    def from_dict(cls, data: dict):
        # Lấy tên của tất cả các fields định nghĩa trong dataclass
        class_fields = {f.name for f in fields(cls)} 
        # Lọc data
        filtered_data = {k: v for k, v in data.items() if k in class_fields}
        ints = cls(**filtered_data)
        if data.get("parameters"):
            for params in data.get("parameters").keys():
                ints.parameters[params] = ParameterProperties.from_dict(
                    data.get("parameters", {}).get(params))
                
        if data.get("request_body"):
            for contentType in data.get("request_body").keys():
                ints.request_body[contentType] = ItemProperties.from_dict(
                    data.get("request_body", {}).get(contentType))
                
        if data.get("responses"):
            for statusCode in data.get("responses").keys():
                ints.responses[statusCode] = ResponseProperties.from_dict(
                    data.get("responses", {}).get(statusCode))
                
        return ints

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    def get_parameters(self, required=False):
        if not self.parameters:
            return []
        
        return remove_nulls([{
            "name": name,
            "type": details.schema.type,
            "description": details.description,
            "enum": details.schema.enum,
            "xrefs": details.schema.xrefs if details.schema.type in ('array', 'object') else None # return xrefs only for complex types
        } for name, details in self.parameters.items()
            if not required or details.required])

    def get_responses(self):
        if self.responses is None:
            return []
        response_list = {}
        for status_code, response_properties in self.responses.items():
            if status_code and isSuccessful(status_code) and response_properties.content:
                for _, response_details in response_properties.content.items():
                    curr_responses = flatten_json_schema(
                        to_dict_helper(response_details))
                    response_list.update(curr_responses)

        return remove_nulls([{
            "name": item.split(".")[-1],
            "full_name": item,
            "type": val.get("type"),
            "description": val.get("description", ""),
            "enum": val.get("enum"),
            "xrefs": val.get("xrefs") if val.get("type") in ('array', 'object') else None  # return xrefs only for complex types
        } for item, val in response_list.items()])

    def get_request_body(self):
        if self.request_body is None:
            return []
        request_body_list = {}
        for content_type, item_properties in self.request_body.items():
            curr_request_body = flatten_json_schema(
                to_dict_helper(item_properties))
            request_body_list.update(curr_request_body)
        return remove_nulls([{
            "name": item,
            "type": val.get("type"),
            "description": val.get("description", ""),
            "enum": val.get("enum"),
            "xrefs": val.get("xrefs")
        } for item, val in request_body_list.items()])
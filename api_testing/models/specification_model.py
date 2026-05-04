

from collections import defaultdict
import copy
import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field, fields
from api_testing.utils import flatten_json_schema, to_dict_helper
from api_testing.utils.common import isEmpty, remove_nulls
from api_testing.utils.http import isSuccessful
from copy import deepcopy

def parse_xrefs(xrefs: str) -> list[str]:
    if not xrefs:
        return []
    return [x.strip() for x in xrefs.split(",") if x.strip()]


def merge_xrefs_str(*xrefs_list: str) -> str:
    seen = set()
    result = []

    for xrefs in xrefs_list:
        for x in parse_xrefs(xrefs):
            if x not in seen:
                seen.add(x)
                result.append(x)

    return ",".join(result)

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
    nullable: Optional[bool] = True
    read_only: Optional[bool] = None
    write_only: Optional[bool] = None
    example: Optional[Union[str, int, float, bool, List, Dict]] = None
    examples: List[Optional[Union[str, int, float, bool, List, Dict]]] = field(
        default_factory=list)
    xrefs: Optional[str] = None
    allOf: Optional[List['ItemProperties']] = field(default_factory=list)
    anyOf: Optional[List['ItemProperties']] = field(default_factory=list)
    oneOf: Optional[List['ItemProperties']] = field(default_factory=list)
    
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
            # 🔥 NEW: handle allOf / anyOf / oneOf
        if data.get("allOf"):
            it.allOf = [ItemProperties.from_dict(x) for x in data["allOf"]]

        if data.get("anyOf"):
            it.anyOf = [ItemProperties.from_dict(x) for x in data["anyOf"]]

        if data.get("oneOf"):
            it.oneOf = [ItemProperties.from_dict(x) for x in data["oneOf"]]
        return it
    
    def merge_allOf(self) -> 'ItemProperties':
        if not self.allOf:
            return self

        merged = copy.deepcopy(self)
        merged.allOf = []

        if merged.properties is None:
            merged.properties = {}
            merged.type = "object"

        required_set = set(merged.required or [])
        merged_xrefs = merged.xrefs or ""

        for schema in self.allOf:
            if not schema:
                continue

            schema = schema.merge_allOf()

            # =========================
            # MERGE PROPERTIES
            # =========================
            if schema.properties:
                for key, val in schema.properties.items():
                    if key in merged.properties:
                        existing = merged.properties[key]
                        if existing.type == "object" and val.type == "object":
                            existing.properties = {
                                **(existing.properties or {}),
                                **(val.properties or {})
                            }
                        else:
                            merged.properties[key] = val
                    else:
                        merged.properties[key] = val

            # =========================
            # MERGE REQUIRED
            # =========================
            if schema.required:
                required_set.update(schema.required)

            # =========================
            # 🔥 MERGE XREFS (STRING)
            # =========================
            merged_xrefs = merge_xrefs_str(merged_xrefs, schema.xrefs)

        merged.required = list(required_set)
        merged.xrefs = merged_xrefs

        return merged


    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    def to_human_readable(self,ingore_type=False):
        if self.allOf:
            merged = self.merge_allOf()
            return merged.to_human_readable(ingore_type)
        if self.anyOf:
            return " or ".join([
                item.to_human_readable(True)
                for item in self.anyOf
            ])

        if self.oneOf:
            return " one of (" + ", ".join([
                item.to_human_readable(True)
                for item in self.oneOf
            ]) + ")"
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

        if self.type == 'object' and self.properties:
            dict_items = {k: v.to_human_readable()
                          for k, v in self.properties.items() if v}
            if self.xrefs is not None:
                return f'a {self.xrefs} object'
                # return f'a {self.xrefs} object with schema ' + json.dumps(dict_items, indent=4)
            return json.dumps(dict_items, indent=2)
        if self.type == 'array':
            if not self.items:
                return "array"
            if self.xrefs:
                return f"array of {self.xrefs} object"
            items = self.items if isinstance(self.items, ItemProperties) else ItemProperties.from_dict(self.items)
            return f"array of {items.to_human_readable()}"            # return dict_items
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
    request_body: Dict[str, ItemProperties] = field(default_factory=dict)
    # status code as first key, then each response with its properties as second dict
    responses: Dict[str, ResponseProperties] = None

    @property
    def minetypes(self) -> list[str]:
        request_mime_types = set(self.request_body.keys()) if self.request_body else set()
        response_mime_types = {
            mime
            for resp in (self.responses or {}).values()
            for mime in (resp.content or {}).keys()
        }
        return list(request_mime_types | response_mime_types)    
    
    # @property
    # def schemas(self) -> Dict[str, ItemProperties]:

    #     grouped: dict[str, dict[str, dict]] = defaultdict(dict)

    #     def parse_xrefs(xrefs: str) -> list[str]:
    #         if not xrefs:
    #             return []
    #         return [x.strip() for x in xrefs.split(",") if x.strip()]

    #     def collect(item: ItemProperties):
    #         if not item:
    #             return

    #         # 🔥 1. flatten trực tiếp
    #         flat = flatten_json_schema(item.to_dict())

    #         # 🔥 2. group theo xrefs của từng field
    #         for field_name, field_props in flat.items():
    #             refs = parse_xrefs(field_props.get("xrefs")) or ["Unknown"]

    #             for ref in refs:
    #                 if field_name not in grouped[ref]:
    #                     grouped[ref][field_name] = field_props
    #                 else:
    #                     # merge nhẹ tránh overwrite
    #                     grouped[ref][field_name] = {
    #                         **field_props,
    #                         **grouped[ref][field_name],
    #                     }

    #     # 🚀 root traversal
    #     for status_code, resp in (self.responses or {}).items():
    #         if not isSuccessful(status_code):
    #             continue

    #         for item in (resp.content or {}).values():
    #             collect(item)

    #     # 🔥 3. convert → ItemProperties object
    #     result: dict[str, ItemProperties] = {}

    #     for xrefs_name, fields_dict in grouped.items():
    #         props: dict[str, ItemProperties] = {}

    #         for field_name, field_props in fields_dict.items():
    #             field_copy = deepcopy(field_props)
    #             field_copy.pop("xrefs", None)

    #             props[field_name] = ItemProperties.from_dict(field_copy)

    #         result[xrefs_name] = ItemProperties(
    #             type="object",
    #             properties=props,
    #             xrefs=xrefs_name
    #         )

    #     return result

    @property
    def schemas(self) -> Dict[str, ItemProperties]:
        relevant_schemas: Dict[str, ItemProperties] = {}

        def parse_xrefs(xrefs: str):
            if not xrefs:
                return []
            return [x.strip() for x in xrefs.split(",") if x.strip()]

        def collect(item: ItemProperties, inherited_xrefs=None):
            if not item:
                return

            inherited_xrefs = inherited_xrefs or []

            # =========================
            # 🔥 1. collect ALL sub trước
            # =========================
            if getattr(item, "allOf", None):
                for sub in item.allOf:
                    collect(sub, inherited_xrefs)

            if getattr(item, "anyOf", None):
                for sub in item.anyOf:
                    collect(sub, inherited_xrefs)

            if getattr(item, "oneOf", None):
                for sub in item.oneOf:
                    collect(sub, inherited_xrefs)

            # =========================
            # 🔥 2. merge allOf
            # =========================
            if getattr(item, "allOf", None):
                item = item.merge_allOf()

            # =========================
            # 🔥 3. resolve xrefs (FIX + INHERIT)
            # =========================
            current_refs = parse_xrefs(item.xrefs)
            effective_refs = current_refs if current_refs else inherited_xrefs

            if effective_refs:
                if item.type in ("object", "array"):
                    for ref in effective_refs:
                        if ref not in relevant_schemas:
                            relevant_schemas[ref] = item
                else:
                    for ref in effective_refs:  # 👈 FIX: loop thay vì dùng ref undefined
                        relevant_schemas.setdefault(ref, item)

            # =========================
            # 🔁 4. recurse (PASS DOWN refs)
            # =========================
            next_inherited = effective_refs

            if item.items:
                collect(item.items, next_inherited)

            if item.properties:
                for prop in item.properties.values():
                    collect(prop, next_inherited)

        # =========================
        # 🚀 root traversal
        # =========================
        for status_code, resp in (self.responses or {}).items():
            if not isSuccessful(status_code):
                continue

            for item in (resp.content or {}).values():
                collect(item)

        return relevant_schemas


    # @property
    # def schemas(self) -> Dict[str, ItemProperties]:
        
    #     def get_relevant_schema_of_endpoint(response: ResponseProperties) -> List[str]:
    #         relevant_schemas = {}

    #         def get_schema_recursive(item_properties: ItemProperties):
    #             if item_properties is None:
    #                 return
    #             if item_properties.xrefs and item_properties.type in ['object', 'array']:
    #                 schema_name = item_properties.xrefs
    #                 if schema_name not in relevant_schemas:
    #                     relevant_schemas[schema_name] = item_properties

    #             if item_properties.items:
    #                 get_schema_recursive(item_properties.items)
    #             if item_properties.properties:
    #                 for prop in item_properties.properties.values():
    #                     get_schema_recursive(prop)

    #         for status_code, properties in response.items():
    #             if isSuccessful(status_code):
    #                 for item_properties in properties.content.values():
    #                     get_schema_recursive(item_properties)
    #         return relevant_schemas

    #     return get_relevant_schema_of_endpoint(self.responses)

    @property
    def required_parameters(self) -> Dict[str, ParameterProperties]:
        # type: ignore
        return {k: v for k, v in self.parameters.items() if v.required}

    @property
    def optional_parameters(self) -> Dict[str, ParameterProperties]:
        return {k: v for k, v in self.parameters.items() if not v.required}
    
    # @property
    # def successful_responses(self) -> ItemProperties:
    #     if self.responses is None:
    #         return None
    #     for status_code, response_properties in self.responses.items():
    #         if status_code and isSuccessful(status_code) and response_properties.content:
    #             for _, response_details in response_properties.content.items():
    #                 return response_details
    #     return None

    @property
    def successful_responses(self) -> Optional[ItemProperties]:
        if not self.responses:
            return None

        collected: list[ItemProperties] = []

        for status_code, resp in self.responses.items():
            if not isSuccessful(status_code):
                continue

            for item in (resp.content or {}).values():
                if not item:
                    continue

                # 🔥 allOf
                if getattr(item, "allOf", None):
                    item = item.merge_allOf()

                # 🔥 array → unwrap
                if item.type == "array" and item.items:
                    item = item.items

                # 🔥 anyOf / oneOf
                if getattr(item, "anyOf", None):
                    collected.extend(item.anyOf)
                    continue

                if getattr(item, "oneOf", None):
                    collected.extend(item.oneOf)
                    continue

                collected.append(item)

        if not collected:
            return None

        return self._merge_item_properties(collected)
    def _merge_item_properties(self, items: list[ItemProperties]) -> ItemProperties:
        merged = ItemProperties(
            type="object",
            properties={},
            required=[],
        )

        merged_xrefs = set()

        for item in items:
            if not item:
                continue

            # 🔥 merge object-level xrefs
            if getattr(item, "xrefs", None):
                merged_xrefs.update(
                    x.strip() for x in item.xrefs.split(",") if x.strip()
                )

            # 🔥 ưu tiên object
            if item.type == "object" and item.properties:
                for k, v in item.properties.items():
                    if k not in merged.properties:
                        merged.properties[k] = v
                    else:
                        existing = merged.properties[k]

                        # 🔥 merge field-level xrefs
                        old_refs = set(
                            x.strip()
                            for x in (getattr(existing, "xrefs", "") or "").split(",")
                            if x.strip()
                        )
                        new_refs = set(
                            x.strip()
                            for x in (getattr(v, "xrefs", "") or "").split(",")
                            if x.strip()
                        )

                        merged_refs = old_refs | new_refs
                        if merged_refs:
                            existing.xrefs = ",".join(sorted(merged_refs))

                # 🔥 merge required
                if item.required:
                    merged.required = list(set(merged.required + item.required))

                # 🔥 propagate parent xrefs → field (optional nhưng rất hữu ích)
                if getattr(item, "xrefs", None):
                    for field in item.properties.values():
                        if not getattr(field, "xrefs", None):
                            field.xrefs = item.xrefs

            else:
                # 🔥 fallback nếu chưa có object nào
                if not merged.properties:
                    merged = item

        # 🔥 set merged object-level xrefs
        if merged_xrefs:
            merged.xrefs = ",".join(sorted(merged_xrefs))

        return merged.merge_allOf()

    # def _merge_item_properties(self, items: list[ItemProperties]) -> ItemProperties:
    #     merged = ItemProperties(
    #         type="object",
    #         properties={},
    #         required=[],
    #     )

    #     for item in items:
    #         if not item:
    #             continue

    #         # ưu tiên object
    #         if item.type == "object" and item.properties:
    #             merged.properties.update(item.properties)

    #             if item.required:
    #                 merged.required = list(set(merged.required + item.required))
    #         else:
    #             # fallback nếu không có object nào
    #             if not merged.properties:
    #                 merged = item

    #     return merged.merge_allOf()
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
        return request_body_list
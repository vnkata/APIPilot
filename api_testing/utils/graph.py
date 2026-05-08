
from copy import copy
from difflib import SequenceMatcher
import re
from typing import Dict, List, Optional

from api_testing.models.specification_model import ItemProperties
from api_testing.utils import flatten_json_schema, handle_word_cases
from sentence_transformers import util


def preprocess_string(s):
    # s = s.lower()
    s = re.sub(r'\{.*?\}', '', s)
    s = re.sub(r"[_]", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def filter_item_properties(item: ItemProperties,
    root_xrefs: Optional[str],
    paths: List[str]
) -> ItemProperties:
    """Return a filtered copy of `item` keeping only properties matching given dot-paths."""
    if not item or not item.properties:
        return item

    # Parse dot paths into nested dict tree
    tree = {}
    for path in paths:
        current = tree
        for part in path.split('.'):
            current = current.setdefault(part, {})

    def _filter_recursive(source: ItemProperties, allowed_tree: Dict[str, dict]) -> ItemProperties:
        if not source or not source.properties:
            return source

        filtered = copy(source)
        filtered.properties = {}

        for prop_name, subtree in allowed_tree.items():
            if prop_name in source.properties:
                if subtree:  # deeper level
                    filtered.properties[prop_name] = _filter_recursive(
                        source.properties[prop_name], subtree
                    )
                else:
                    filtered.properties[prop_name] = copy(source.properties[prop_name])
        return filtered

    return _filter_recursive(item, tree)

def normalize_xref(values, target):
    xrefs = values.get("xrefs")
    if not xrefs:
        return None

    if isinstance(xrefs, str):
        xrefs_list = [x.strip() for x in xrefs.split(",") if x.strip()]
    else:
        xrefs_list = xrefs

    if target in xrefs_list:
        # 👇 rewrite lại chỉ giữ đúng schema.xrefs
        new_values = dict(values)
        new_values["xrefs"] = target
        return new_values

    return None

def get_best_mathching_schema(embedding_model, operation, schemas, threshold=0.7, path_tree=""):
    endpoint = operation.endpoint_path
    common_path = endpoint
    endpoint = endpoint.replace(path_tree, "") # only get relative path
    endpoint = preprocess_string(endpoint)
    
    def lookup_string(path: str, param) -> str | None:
        if param.in_value != "path":
            return None
        match = re.search(rf"\{{{re.escape(param.name)}\}}", path)
        if not match:
            return None
        return (
            path[:match.end()]
            .replace("/", " ")
            .replace("{", "")
            .replace("}", "")
            .lower()
        )

    parameters = [
        f"{lookup_string(common_path, p) or handle_word_cases(f'{endpoint}_{p.name}')} {p.to_human_readable()}".lower()
        for p in operation.parameters.values()
    ]
    # combine with req_body
    for k,v in operation.get_request_body().items():
        combined = handle_word_cases((v.get("xrefs") or '') + "_" + k)
        readable = ItemProperties.from_dict(v).to_human_readable()
        parameters.append(f"{combined} {readable}")
    
    if len(parameters) == 0:
        return {}
    parameter_embeddings = embedding_model.embed_texts(parameters)
    keep_schemas = {}
    for schema_name, schema in schemas.items():
        if schema is not None:
            # flattened_schema = {
            #     field: values
            #     for field, values in flatten_json_schema(schema.to_dict()).items()
            #     # if (
            #     #     (schema.xrefs is None and values.get("xrefs") is None)
            #     #     or (schema.xrefs is not None and values.get("xrefs") == schema.xrefs)
            #     # )
            # }
            flattened = flatten_json_schema(schema.to_dict())
            flattened_schema = {}

            for field, values in flattened.items():
                normalized = normalize_xref(values, schema_name)
                if normalized:
                    flattened_schema[field] = normalized
            
            # attributes = [field for field, values in flattened_schema.items() if values.get('type') not in ['object', 'array', None]]
            attributes = [field for field, values in flattened_schema.items()]   

            attributes_texts = []
            for field, values in flattened_schema.items():
                if values.get('type') not in ['object', 'array', None]:
                    xrefs = values.get('xrefs', '')
                    # field_name = field.split('.')[-1]
                    path_context = field.replace('.', ' ')
                    combined = handle_word_cases(xrefs + "_" + path_context)
                    readable = ItemProperties(**values).to_human_readable()
                    attributes_texts.append(f"{combined} {readable}")

            attributes_embedding = embedding_model.embed_texts(attributes_texts)
            
            hits = util.semantic_search(parameter_embeddings, attributes_embedding, top_k=100)
            keep_attributes = {}
            for param_i in range(len(hits)):
                for hit in hits[param_i]:
                    attribute = attributes[hit["corpus_id"]]
                    score = hit["score"]
                    if score >= threshold:
                        keep_attributes[attribute] = score
            schema = filter_item_properties(schema, root_xrefs=schema.xrefs, paths=list(keep_attributes.keys()))
            if len(keep_attributes) > 0:
                keep_schemas[schema_name] = schema
    return keep_schemas


def is_nested_path_end_with(
    nested_path: str,
    ending_path: str,
    delimiter: str = '.',
    equal=False
) -> bool:
    def normalize(path: str) -> List[str]:
        return [seg for seg in path.replace("[]", "").split(delimiter) if seg]

    nested_segments = normalize(nested_path)
    ending_segments = normalize(ending_path)

    if len(ending_segments) > len(nested_segments):
        return False
    if equal and len(ending_segments) != len(nested_segments):
        return False
    return nested_segments[-len(ending_segments):] == ending_segments

# def is_nested_path_end_with(
#     nested_path: str, 
#     ending_path: str,
#     delimiter: str = '.'
# ) -> bool:
#     nested_path = nested_path.replace("[]", "")  # Remove array indicators
#     ending_path = ending_path.replace("[]", "")
#     segments: List[str] = nested_path.split(delimiter)
#     ending_segment: List[str] = ending_path.split(delimiter)
#     if not segments or not ending_segment:
#         return False
        
#     last_segment: str = segments[-1]
#     ending_segment: str = ending_segment[-1]

#     return last_segment == ending_segment
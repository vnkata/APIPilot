
from copy import copy
from difflib import SequenceMatcher
import re
from typing import Dict, List, Optional

from api_testing.models.specification_model import ItemProperties
from api_testing.utils import flatten_json_schema, handle_word_cases
from sentence_transformers import util


def remove_path_variables(string):
    pattern = r'\{.*?\}'
    result = re.sub(pattern, '', string)
    return result

def preprocess_string(s):
    # s = s.lower()
    s = re.sub(r'\{.*?\}', '', s)
    s = re.sub(r"[_]", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def levenshtein_ratio(s1, s2):
    return SequenceMatcher(None, s1, s2).ratio()



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


def get_best_mathching_schema(embedding_model, operation, schemas, threshold=0.7, path_tree=""):
    endpoint = operation.endpoint_path
    endpoint = endpoint.replace(path_tree, "") # only get relative path
    endpoint = preprocess_string(endpoint)
    
    parameters = [ f"{handle_word_cases(endpoint + "_" + param.name)} {param.to_human_readable()}".lower() for param in operation.parameters.values()]
    if len(parameters) == 0:
        return {}
    parameter_embeddings = embedding_model.embed_texts(parameters)
    keep_schemas = {}
    for schema_name, schema in schemas.items():
        if schema is not None:
            flattened_schema = {
                field: values
                for field, values in flatten_json_schema(schema.to_dict()).items()
                if (
                    (schema.xrefs is None and values.get("xrefs") is None)
                    or (schema.xrefs is not None and values.get("xrefs") == schema.xrefs)
                )
            }
            attributes = [ field for field, values in flattened_schema.items() if values.get('type') not in ['object','array', None]]
            attributes_texts = [ f"{ handle_word_cases(values.get('xrefs','') + "_" + field.split('.')[-1])} {ItemProperties(**values).to_human_readable()}" for field, values in flattened_schema.items() if values.get('type') not in ['object','array', None]]
            attributes_embedding = embedding_model.embed_texts(attributes_texts)
            
            hits = util.semantic_search(parameter_embeddings, attributes_embedding)
            keep_attributes = {}
            for param_i in range(len(hits)):
                for hit in hits[param_i]:
                    attribute = attributes[hit["corpus_id"]]
                    score = hit["score"]
                    if score >= threshold:
                        keep_attributes[attribute] = score
            schema = filter_item_properties(schema, root_xrefs=schema.xrefs, paths=list(keep_attributes.keys()))
            print(keep_attributes)
            if len(keep_attributes) > 0:
                keep_schemas[schema_name] = schema
    return keep_schemas

    
def is_nested_path_end_with(
    nested_path: str, 
    ending_path: str,
    delimiter: str = '.'
) -> bool:
    segments: List[str] = nested_path.split(delimiter)
    ending_segment: List[str] = ending_path.split(delimiter)
    if not segments or not ending_segment:
        return False
        
    last_segment: str = segments[-1]
    ending_segment: str = ending_segment[-1]

    return last_segment == ending_segment
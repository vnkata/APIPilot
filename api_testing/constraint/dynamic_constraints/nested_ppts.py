"""PPT nesting handling for Beet.

@author: Juan C. Alonso
"""

from typing import List, Dict, Any, Optional
from api_testing.constraint.dynamic_constraints.decls_exit import DeclsExit
from api_testing.constraint.dynamic_constraints.variable.variable_utils import ARRAY_NESTING_SEPARATOR, ARRAY_TYPE_NAME, HIERARCHY_SEPARATOR, OBJECT_TYPE_NAME, PRIMITIVE_TYPES, translate_datatype
from api_testing.models.specification_model import ItemProperties


def get_all_nested_decls_exits(
    endpoint: str,
    operation_name: str,
    variable_name_input: str,
    enter_variables,
    output_object_name: str,
    media_type: ItemProperties,
    status_code: str
) -> List[DeclsExit]:
    """Get all nested exits for different response codes.
    
    Args:
        endpoint: API endpoint
        operation_name: Operation name
        variable_name_input: Input variable name
        enter_variables: Enter variables
        output_object_name: Output object name
        media_type: Media type of response
        status_code: HTTP status code
        
    Returns:
        List of DeclsExit objects
    """
    res: List[DeclsExit] = []
    parameter_type = media_type.type
    map_of_properties = media_type
    if (
        parameter_type
        and parameter_type.lower() == ARRAY_TYPE_NAME
    ):
        # Get the schema as ArraySchema
        array_schema = media_type
        # name_suffix = parent_variable
        name_suffix = (
            ARRAY_NESTING_SEPARATOR + "array"
        )

        while parameter_type and parameter_type.lower() == ARRAY_TYPE_NAME:
            decls_exit = DeclsExit(
                endpoint,
                operation_name,
                variable_name_input,
                enter_variables,
                output_object_name,
                array_schema,
                "array",
                name_suffix,
                status_code,
            )
            res.append(decls_exit)

            parameter_type = (
                array_schema.items.type if array_schema.items else None
            )

            if parameter_type and parameter_type.lower() == ARRAY_TYPE_NAME:
                array_schema = array_schema.items
            else:
                map_of_properties = array_schema.items

            name_suffix = (
                name_suffix
                + ARRAY_NESTING_SEPARATOR
                + "array"
            )

    elif (
        parameter_type
        and translate_datatype(parameter_type)
        in PRIMITIVE_TYPES
    ):
        primitive_exit = DeclsExit(
            endpoint,
            operation_name,
            variable_name_input,
            enter_variables,
            output_object_name,
            parameter_type,
            status_code,
        )
        return [primitive_exit]

    # Create DeclsObjects with the elements of the array
    # If there is an allOf, parameter_type is None, but the schema contains all the properties
    if parameter_type is None or parameter_type.lower() == OBJECT_TYPE_NAME:
        all_schemas: Dict[str, Any] = {}

        all_schemas[""] = map_of_properties
        all_schemas.update(get_all_nested_schemas("", map_of_properties))

        for name_suffix in all_schemas.keys():
            schema = all_schemas[name_suffix]
            schema_type = schema.type if hasattr(schema, "type") else None

            # If the element is of type array
            if schema_type and schema_type.lower() == "array":
                array_schema = schema
                decls_exit = DeclsExit(
                    endpoint,
                    operation_name,
                    variable_name_input,
                    enter_variables,
                    output_object_name,
                    array_schema,
                    name_suffix,
                    name_suffix,
                    status_code,
                )
                res.append(decls_exit)
            else:  # If the element is of type object
                decls_exit = DeclsExit(
                    endpoint,
                    operation_name,
                    variable_name_input,
                    enter_variables,
                    output_object_name,
                    schema,
                    name_suffix,
                    status_code,
                )
                res.append(decls_exit)

    return res


def get_all_nested_schemas(
    name_suffix: str, map_of_properties: ItemProperties
) -> Dict[str, ItemProperties]:
    """Get all nested schemas recursively.
    
    Args:
        name_suffix: Name suffix for the current schema
        map_of_properties: ItemProperties schema object
        
    Returns:
        Dictionary of nested schemas
    """
    res: Dict[str, ItemProperties] = {}
    if not hasattr(map_of_properties, "properties") or map_of_properties.properties is None:
        return res
    properties = map_of_properties.properties
    # Warnings if properties is None
    if properties is None:
        additional_properties = map_of_properties.additional_properties
        if additional_properties is None:
            print(
                f"WARNING: No properties found for object: {name_suffix}"
            )
        else:
            print(
                f"WARNING: Object: {name_suffix} only contains additional properties"
            )
    else:
        parameter_names = properties.keys()

        for parameter_name in parameter_names:
            schema = properties[parameter_name]
            if schema is None:
                print(
                    f"WARNING: No schema found for parameter: {parameter_name} in object: {name_suffix}"
                )
                continue
            parameter_type = schema.type

            # If there is an allOf, parameter_type is None, but the schema contains all the properties
            if parameter_type is None or (
                parameter_type and parameter_type.lower() == OBJECT_TYPE_NAME
            ):  # If object
                # Recursive call with object.get_parameter
                res.update(
                    get_all_nested_schemas(
                        name_suffix
                        + HIERARCHY_SEPARATOR
                        + parameter_name,
                        schema,
                    )
                )

            elif parameter_type and parameter_type.lower() == ARRAY_TYPE_NAME:  # If array
                array_schema = properties[parameter_name]
                items_datatype = (
                    array_schema.items.type
                    if array_schema.items
                    else None
                )
                nesting_suffix = (
                    ARRAY_NESTING_SEPARATOR + "array"
                )

                # If there is an allOf, parameter_type is None, but the schema contains all the properties
                while (
                    items_datatype
                    and items_datatype.lower() == ARRAY_TYPE_NAME
                ):
                    array_schema = array_schema.items
                    res[
                        name_suffix
                        + HIERARCHY_SEPARATOR
                        + parameter_name
                        + nesting_suffix
                    ] = array_schema
                    items_datatype = (
                        array_schema.items.type
                        if array_schema.items
                        else None
                    )
                    nesting_suffix += (
                        ARRAY_NESTING_SEPARATOR
                        + "array"
                    )

                # If there is an allOf, parameter_type is None, but the schema contains all the properties
                if items_datatype is None or (
                    items_datatype
                    and items_datatype.lower() == OBJECT_TYPE_NAME
                ):
                    sub_schema = array_schema.items

                    res[
                        name_suffix
                        + HIERARCHY_SEPARATOR
                        + parameter_name
                    ] = sub_schema

                    res.update(
                        get_all_nested_schemas(
                            name_suffix
                            + HIERARCHY_SEPARATOR
                            + parameter_name,
                            sub_schema,
                        )
                    )

    return res

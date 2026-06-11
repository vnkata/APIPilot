from lark import Transformer, v_args

from .dsl_value import DSLValue
from .functions import RuleFunctions


@v_args(inline=True)
class DSLTransformer(Transformer):

    SPECIAL_MAP = {
        "in": "is_in",
        "and": "and_op",
        "or": "or_op",
        "not": "not_op",
        "str": "to_string",
        "size": "size_of",
        "sizeOf": "size_of",
        "length": "length",
        "isNull": "is_null",
        "toString": "to_string",
        "toBool": "to_bool",
        "toInt": "to_int",
        "toNumber": "to_number",
        "isEmail": "is_email",
        "isURL": "is_url",
        "isDate": "is_date",
        "isRegex": "is_regex",
        "isSortedBy": "is_sorted_by",
        "isNumeric": "is_numeric",
        "isSubstring": "is_substring",
        "isTimestamp": "is_timestamp",
        "isDateTime": "is_timestamp",
        "oneOf": "one_of"
    }

    AGGREGATE_FUNCTIONS = {
        "is_sorted_by"
    }

    SPECIAL_FUNCTIONS = {
        "size_of",
        "length"
    }

    def __init__(self, context):

        self.context = context
        self.funcs = RuleFunctions()

        from api_testing.utils.log import getLogger
        self.logger = getLogger(__name__)

    # =====================================================
    # Literals
    # =====================================================

    def string(self, value):
        return DSLValue(
            value=value.strip("'\"")
        )

    def number(self, value):

        value = str(value)

        try:
            if "." in value:
                return DSLValue(float(value))

            return DSLValue(int(value))

        except Exception:
            return DSLValue(float(value))

    def list(self, *items):

        return DSLValue(
            value=[
                self._unwrap(item)
                for item in items
            ]
        )

    # =====================================================
    # Variables
    # =====================================================

    def variable(self, name):

        key = str(name)

        try:

            value = (
                self.context.get(key)
                if hasattr(self.context, "get")
                else self.context.get(key, None)
            )

            return DSLValue(
                value=value,
                path=key
            )

        except Exception as ex:

            self.logger.error(
                f"Variable resolve error: {key} -> {ex}"
            )

            return DSLValue(
                value=None,
                path=key
            )

    # =====================================================
    # Expressions
    # =====================================================

    def func_call(self, name, *args):
        return self.func(name, *args)

    def expr(self, name, *args):
        return self.func(name, *args)

    # =====================================================
    # Dispatcher
    # =====================================================

    def func(self, name, *args):

        raw_name = str(name)

        method_name = (
            self.SPECIAL_MAP.get(raw_name)
            or self._camel_to_snake(raw_name)
        )

        func_ptr = getattr(
            self.funcs,
            method_name,
            None
        )

        if func_ptr is None:
            raise AttributeError(
                f"Undefined DSL function: {raw_name}"
            )

        try:

            result = self._invoke(
                method_name,
                func_ptr,
                *args
            )

            if result is False:
                self.logger.warning(
                    f"DSL validation failed: "
                    f"{raw_name}{args}"
                )

            if isinstance(result, DSLValue):
                return result
            # print(
            #     "FUNC =", raw_name,
            #     "ARGS =",
            #     [getattr(a, "value", a) for a in args],
            #     "RESULT =",
            #     result
            # )
            return DSLValue(result)

        except Exception as ex:

            self.logger.error(
                f"DSL function error: "
                f"{raw_name}{args} -> {ex}"
            )

            raise

    # =====================================================
    # Invocation Engine
    # =====================================================

    def _invoke(
        self,
        method_name,
        func_ptr,
        *args
    ):

        # ----------------------------------
        # Special polymorphic functions
        # ----------------------------------

        if method_name in self.SPECIAL_FUNCTIONS:
            return self._handle_special_function(
                method_name,
                func_ptr,
                *args
            )

        # ----------------------------------
        # Aggregate functions
        # ----------------------------------

        if method_name in self.AGGREGATE_FUNCTIONS:

            return func_ptr(
                *[
                    self._unwrap(arg)
                    for arg in args
                ]
            )

        # ----------------------------------
        # Find projected arrays
        # ----------------------------------

        projected_args = []
        for arg in args:
            if (
                isinstance(arg, DSLValue)
                and arg.is_projected_array
            ):
                # NẾU là hàm đặc biệt (size, length) VÀ đường dẫn kết thúc bằng []
                # THÌ bỏ qua, không đưa vào danh sách lặp (Zip semantics)
                if method_name in self.SPECIAL_FUNCTIONS and arg.path.endswith("[]"):
                    continue
                
                projected_args.append(arg)    

        for arg in projected_args:
            if arg.value is None:
                arg.value = []  
            elif not isinstance(arg.value, (list, tuple)):
                arg.value = [arg.value] 
        # exempt_methods = {
        #     "to_bool", "to_int", "to_string", "to_number", 
        #     "default", "size_of", "length", "is_null", "isDate"
        # }
        exempt_methods = {"is_null", "isNull", "default"}
        # ----------------------------------
        # Scalar call
        # ----------------------------------

        if not projected_args:

            values = [
                self._unwrap(arg)
                for arg in args
            ]

            # if any(v is None for v in values):
            #     return True
            if method_name not in exempt_methods:
                if any(v is None for v in values):
                    return True
            return func_ptr(*values)

        # ----------------------------------
        # Cardinality validation
        # ----------------------------------

        expected_size = len(
            projected_args[0].value
        )

        for projected in projected_args:

            if len(projected.value) != expected_size:
                raise ValueError(
                    f"Collection size mismatch: "
                    f"{projected.path}"
                )

        # ----------------------------------
        # Zip semantics
        # ----------------------------------

        results = []

        for index in range(expected_size):

            current_args = []

            for arg in args:

                if (
                    isinstance(arg, DSLValue)
                    and arg.is_projected_array
                    and isinstance(arg.value, list)
                ):
                    current_args.append(
                        arg.value[index]
                    )
                else:
                    current_args.append(
                        self._unwrap(arg)
                    )

            # # vacuous truth
            if any(v is None for v in current_args):
                if method_name not in exempt_methods:
                    results.append(True)
                    continue

            results.append(
                func_ptr(*current_args)
            )
        casting_methods = {
            "to_bool", "to_int", "to_string", "to_number", "default"
        }

        if method_name in casting_methods:
            return DSLValue(
                value=results,
                path=projected_args[0].path 
            )
        return all(results)

    # =====================================================
    # Special Functions
    # =====================================================

    def _handle_special_function(
        self,
        method_name,
        func_ptr,
        arg
    ):

        if not isinstance(arg, DSLValue):
            return func_ptr(arg)
        
        if arg.value is None:
            return DSLValue(None, path=arg.path)
        
        # return.provinces[]
        if arg.is_array_node:
            return func_ptr(arg.value)

        # return.provinces[].id
        if arg.is_projected_array:

            return DSLValue(
                value=[
                    func_ptr(item)
                    for item in arg.value
                ],
                path=arg.path
            )

        return func_ptr(arg.value)

    # =====================================================
    # Helpers
    # =====================================================

    @staticmethod
    def _unwrap(value):

        if isinstance(value, DSLValue):
            return value.value

        return value

    @staticmethod
    def _camel_to_snake(name):

        chars = []

        for c in name:

            if c.isupper():
                chars.append("_")
                chars.append(c.lower())
            else:
                chars.append(c)

        return "".join(chars).lstrip("_")
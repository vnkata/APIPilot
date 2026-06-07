
from lark import Transformer, v_args
from .functions import RuleFunctions


@v_args(inline=True)
class DSLTransformer(Transformer):
    def __init__(self, context):
        self.context = context
        self.funcs = RuleFunctions()
        from api_testing.utils.log import getLogger
        self.logger = getLogger(__name__)

    # ===== Basic types =====
    def string(self, s):
        return s.strip("'\"")

    def number(self, n):
        return float(n)

    def list(self, *items):
        return list(items)

    # =========================================================
    # 🔥 FLAT VARIABLE RESOLVER (KHÔNG nested, KHÔNG split ".")
    # =========================================================
    def variable(self, name):
        key = str(name)

        try:
            # support DSLEvaluationContext hoặc dict
            if hasattr(self.context, "get"):
                value = self.context.get(key)
            else:
                value = self.context.get(key, None)

            return value

        except Exception as e:
            self.logger.error(f"Variable resolve error: {key} -> {e}")
            return None

    # =========================================================
    # 🔥 FUNCTION DISPATCH + VECTORIZE
    # =========================================================
    def func(self, name, *args):
        raw_name = str(name)

        special_map = {
            "in": "is_in",
            "and": "and_op",
            "or": "or_op",
            "not": "not_op",
            "str": "to_string",
            "sizeOf": "size_of",
            "isNull": "is_null",
            "toString": "to_string",
            "isEmail": "is_email",
            "isURL": "is_url",
            "isDate": "is_date",
            "isRegex": "is_regex",
            "isSortedBy": "is_sorted_by",
            "isNumeric": "is_numeric",
            "oneOf": "one_of"
        }

        method_name = special_map.get(raw_name) or ''.join(
            ['_' + c.lower() if c.isupper() else c for c in raw_name]
        ).lstrip('_')

        func_ptr = getattr(self.funcs, method_name, None)

        if not func_ptr:
            raise AttributeError(f"Undefined DSL function: {raw_name}")

        try:
            
            if any(arg is None for arg in args):
                return None

            result = func_ptr(*args)

            if result is False:
                self.logger.warning(
                    f"DSL validation failed: {args} {raw_name}({', '.join(map(str, args))})"
                )
            return result

        except Exception as e:
            self.logger.error(
                f"DSL function error: {raw_name}({args}) -> {e}"
            )
            raise

    def func_call(self, name, *args):
        return self.func(name, *args)

    def expr(self, name, *args):
        return self.func(name, *args)

    # ===== Utility =====
    @staticmethod
    def all_op(collection, evaluator_fn):
        if not isinstance(collection, list):
            return False
        if not collection:
            return True
        return all(evaluator_fn(item) for item in collection)
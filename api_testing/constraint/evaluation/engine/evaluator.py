from lark import Transformer, v_args
from .functions import RuleFunctions

@v_args(inline=True)
class DSLTransformer(Transformer):
    def __init__(self, context):
        self.context = context
        self.funcs = RuleFunctions()

    # Xử lý các kiểu dữ liệu cơ bản
    def string(self, s): return s.strip("'\"")
    def number(self, n): return float(n)
    def list(self, *items): return list(items)
    
    def variable(self, name):
        # Truy xuất sâu nếu cần (ví dụ: "user.id")
        return self.context.get(str(name))

    def func(self, name, *args):
        raw_name = str(name)
        
        # Mapping các trường hợp đặc biệt
        special_map = {
            "in": "is_in",
            "and": "and_op",
            "or": "or_op",
            "not": "not_op"
        }
        
        if raw_name in special_map:
            method_name = special_map[raw_name]
        else:
            # Chuyển camelCase (sizeOf) -> snake_case (size_of)
            method_name = ''.join(['_' + i.lower() if i.isupper() else i for i in raw_name]).lstrip('_')

        func_ptr = getattr(self.funcs, method_name, None)
        if func_ptr:
            return func_ptr(*args)
            
        raise AttributeError(f"Quy tắc '{raw_name}' chưa được định nghĩa.")

    def expr(self, name, *args):
        return self.func(name, *args)
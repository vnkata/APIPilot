import re
from datetime import datetime

class RuleFunctions:
    # --- Logical Operators ---
    @staticmethod
    def eq(a, b): 
        a_num = int(a)
        b_num = int(b)
        if a_num is not None and b_num is not None:
            return a_num == b_num

    @staticmethod
    def neq(a, b): return a != b

    @staticmethod
    def gt(a, b): return a > b

    @staticmethod
    def gte(a, b): 
        a_num = int(a)
        b_num = int(b)
        if a_num is not None and b_num is not None:
            return a_num >= b_num

    @staticmethod
    def lt(a, b): return a < b

    @staticmethod
    def lte(a, b): 
        a_num = int(a)
        b_num = int(b)
        if a_num is not None and b_num is not None:
            return a_num <= b_num

    @staticmethod
    def and_op(*args): return all(args)

    @staticmethod
    def or_op(*args): return any(args)

    @staticmethod
    def not_op(a): return not a

    @staticmethod
    def implies(p, q):
        # P -> Q is equivalent to (not P) or Q
        return (not p) or q

    # --- Set & Collection Operators ---
    @staticmethod
    def is_in(a, b_list): 
        return a in b_list if isinstance(b_list, list) else False

    @staticmethod
    def size_of(val):
        try:
            return len(val)
        except Exception as e:
            print(f"Error in size_of: {e}") 
            return 0

    @staticmethod
    def contains(collection, item):
        try:
            return item in collection
        except: return False

    @staticmethod
    def default(val, fallback):
        return val if val is not None else fallback

    @staticmethod
    def is_null(val):
        return val is None

    @staticmethod
    def to_string(val):
        return str(val)

    # --- API / Validation Functions ---
    @staticmethod
    def is_email(val):
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(pattern, str(val)))

    @staticmethod
    def is_url(val):
        pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return bool(re.match(pattern, str(val)))

    @staticmethod
    def is_date(val):
        try:
            # Hỗ trợ ISO format phổ biến từ JSON
            datetime.fromisoformat(str(val).replace('Z', '+00:00'))
            return True
        except: return False

    @staticmethod
    def between(val, low, high):
        return low <= val <= high

    @staticmethod
    def is_regex(val, pattern):
        try:
            return bool(re.search(pattern, str(val)))
        except: return False

    @staticmethod
    def is_sorted_by(collection, key):
        """
        Kiểm tra mảng object có được sắp xếp theo field 'key' không.
        Ví dụ: isSortedBy(items, 'date')
        """
        if not isinstance(collection, list) or len(collection) < 2:
            return True
        try:
            values = [item.get(key) for item in collection]
            return values == sorted(values)
        except: return False
        
    @staticmethod
    def substring(val, start, end):
        try:
            return str(val)[int(start):int(end)]
        except: return ""

    @staticmethod
    def exists(val):
        return val is not None
    
    @staticmethod
    def all_op(collection, evaluator_fn):
        if not isinstance(collection, list): return False
        if not collection: return True # Empty list thỏa mãn 'all'
        return all(evaluator_fn(item) for item in collection)
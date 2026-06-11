import re
from datetime import datetime

FORMAT_MAP = {
    "YYYY": "%Y",
    "YY": "%y",
    "MM": "%m",
    "DD": "%d",
    "HH": "%H",
    "mm": "%M",
    "ss": "%S",
}

def to_python_datetime_format(fmt: str) -> str:

    result = fmt

    for src, dst in sorted(
        FORMAT_MAP.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):
        result = result.replace(src, dst)

    return result

class RuleFunctions:
    # --- Logical Operators ---
    @staticmethod
    def eq(a, b):
        # 1. Xử lý so sánh List (đệ quy từng phần tử)
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                return False
            return all(RuleFunctions.eq(x, y) for x, y in zip(a, b))
        
        if isinstance(a, list):
            return all(RuleFunctions.eq(x, b) for x in a)
        if isinstance(b, list):
            return all(RuleFunctions.eq(a, y) for y in b)

        # 2. So sánh trực tiếp (ưu tiên nhánh chạy nhanh nhất)
        if a == b:
            return True

        # 3. So sánh dạng Số
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            pass

        # 4. So sánh dạng Datetime (Xử lý hậu tố "Z")
        try:
            a_str = str(a).strip().replace("Z", "+00:00")
            b_str = str(b).strip().replace("Z", "+00:00")
            return datetime.fromisoformat(a_str) == datetime.fromisoformat(b_str)
        except (TypeError, ValueError):
            pass

        # 5. Fallback (Các kiểu dữ liệu khác không bằng nhau)
        return False

    @staticmethod
    def neq(a, b):
        # Phủ định lại kết quả của hàm eq để đảm bảo logic luôn đồng nhất
        return not RuleFunctions.eq(a, b)

    @staticmethod
    def gt(a, b):
        # 1. Xử lý so sánh List
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                return False
            return all(RuleFunctions.gt(x, y) for x, y in zip(a, b))
        
        if isinstance(a, list):
            return all(RuleFunctions.gt(x, b) for x in a)
        if isinstance(b, list):
            return all(RuleFunctions.gt(a, y) for y in b)

        # 2. So sánh dạng Số
        try:
            return float(a) > float(b)
        except (TypeError, ValueError):
            pass
            
        # 3. So sánh dạng Datetime
        try:
            a_str = str(a).strip().replace("Z", "+00:00")
            b_str = str(b).strip().replace("Z", "+00:00")
            return datetime.fromisoformat(a_str) > datetime.fromisoformat(b_str)
        except (TypeError, ValueError):
            pass  

        # 4. Fallback mặc định
        try:
            return a > b
        except Exception:
            return False
    @staticmethod
    def gte(a, b):
        # 1. Handle element-by-element comparison if both are lists
        if isinstance(a, list) and isinstance(b, list):
            # If lengths don't match, they can't be strictly compared index-by-index
            if len(a) != len(b):
                return False
            return all(RuleFunctions.gte(x, y) for x, y in zip(a, b))
        
        # 2. Handle cases where one is a list and the other is a scalar value
        if isinstance(a, list):
            return all(RuleFunctions.gte(x, b) for x in a)
        if isinstance(b, list):
            return all(RuleFunctions.gte(a, y) for y in b)

        # 3. Numeric comparison
        try:
            a_num = float(a)
            b_num = float(b)
            return a_num >= b_num
        except (TypeError, ValueError):
            pass
            
        # 4. Datetime comparison
        try:
            # Replace 'Z' with '+00:00' for compatibility with older Python versions
            a_str = str(a).strip().replace("Z", "+00:00")
            b_str = str(b).strip().replace("Z", "+00:00")
            
            a_dt = datetime.fromisoformat(a_str)
            b_dt = datetime.fromisoformat(b_str)
            return a_dt >= b_dt
        except (TypeError, ValueError):
            pass  

        # 5. Fallback generic comparison (handles strings, etc.)
        try:
            return a >= b
        except Exception:
            return False
        
    @staticmethod
    def is_substring(a, b):
        if a is None or b is None:
            return False
        return str(a) in str(b)
    
    @staticmethod
    def is_timestamp(val, fmt_string=None):
        """
        Wrapper gọi lại is_date.
        Phớt lờ fmt_string từ DSL ("YYYY-MM-DDTHH:MM:SS.mmZ") 
        và luôn dùng chuẩn "iso" để hỗ trợ "optional milliseconds" tự động.
        """
        return RuleFunctions.is_date(val, format="iso")
    
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

        if not isinstance(b_list, list):
            return False

        if isinstance(a, list):
            return all(item in b_list for item in a)

        return a in b_list

    @staticmethod
    def size_of(val):
        try:
            return len(val)
        except Exception as e:
            print(f"Error in size_of: {e}") 
            return 0
    @staticmethod
    def length(val):
        try:
            return len(val)
        except Exception as e:
            print(f"Error in size_of: {e}") 
            return 0
    
    @staticmethod
    def contains(collection, item):
        try:
            return item in collection
        except: 
            return False

    @staticmethod
    def default(val, fallback):
        return val if val is not None else fallback

    @staticmethod
    def is_null(val):
        return val is None

    @staticmethod
    def to_string(val):
        return str(val)
    
    
    @staticmethod
    def to_bool(val):
        if isinstance(val, bool):
            return val
        if val is None:
            return False
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return val.strip().lower() in {
                "true",
                "1",
                "yes",
                "y",
                "on",
                "t",
            }
        return bool(val)
    @staticmethod
    def to_number(val):
        if val is None:
            return None
        if isinstance(val, bool):
            return int(val)
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            try:
                num = float(val)
                if num.is_integer():
                    return int(num)

                return num

            except ValueError:
                return None
        return None
    @staticmethod
    def to_int(val):

        if val is None:
            return None

        if isinstance(val, bool):
            return int(val)

        if isinstance(val, int):
            return val

        if isinstance(val, float):
            return int(val)

        if isinstance(val, str):

            val = val.strip()

            if not val:
                return None

            try:
                return int(float(val))

            except ValueError:
                return None

        return None
    # --- API / Validation Functions ---
    @staticmethod
    def is_email(val):
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if isinstance(val, list):
            return all(
                RuleFunctions.is_email(item)
                for item in val
            )
        return bool(re.match(pattern, str(val)))

    @staticmethod
    def is_url(val):
        # pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        pattern = r'^(https?://[^\s]+|[\w.-]+@[\w.-]+:[\w./-]+)$'
        if isinstance(val, list):
            return all(
                RuleFunctions.is_url(item)
                for item in val
            )
        return bool(re.match(pattern, str(val)))

    @staticmethod
    def is_date(val, format="iso"):
        """
        Check whether a value matches a date/datetime format.

        ```
        Args:
            val: value to validate.
            format: a format string, "iso", or a list of formats.

        Returns:
            bool
        """
        formats = format if isinstance(format, list) else [format]
        if isinstance(val, list):
            return all(
                RuleFunctions.is_date(item, format)
                for item in val
            )
        for fmt in formats:
            try:
                if fmt == "iso":
                    datetime.fromisoformat(
                        str(val).replace("Z", "+00:00")
                    )
                else:
                    fmt = to_python_datetime_format(fmt)
                    datetime.strptime(str(val), fmt)
                return True
            except (ValueError, TypeError):
                continue
        return False


    @staticmethod
    def between(val, low, high):
        return low <= val <= high

    @staticmethod
    def is_regex(val, pattern):
        if isinstance(val, list):
            return all(
                RuleFunctions.is_regex(item)
                for item in val 
            ) 
        try:
            pattern = pattern.replace('\\\\', '\\')
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
    
from dataclasses import dataclass
from typing import Any


@dataclass
class DSLValue:

    value: Any
    path: str | None = None

    @property
    def is_array_node(self):
        return bool(
            self.path
            and self.path.endswith("[]")
        )

    @property
    def is_projected_array(self):
        """
        Đơn giản hóa: Chỉ cần path có chứa '[]' là nó ĐÃ HOẶC SẼ LÀ một mảng được chiếu.
        Bỏ check isinstance(..., list) ở đây để tránh bẫy kiểu dữ liệu của các thư viện bên thứ 3.
        """
        return bool(
            self.path
            and "[]" in self.path
        )

    @property
    def wildcard_depth(self):
        if not self.path:
            return 0

        return self.path.count("[]")
    
    def __bool__(self):
        # Ép kiểu an toàn, hỗ trợ cả list, tuple hoặc generator đã ép sang list
        if isinstance(self.value, (list, tuple)):
            return len(self.value) > 0
        return bool(self.value)
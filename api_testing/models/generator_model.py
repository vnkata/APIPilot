from dataclasses import dataclass, fields
from typing import Any, Optional
from api_testing.inputs import RandomGeneratorFactory
from api_testing.inputs.random_generator import RandomGenerator
from .configuration_model import FieldConfiguration
from .specification_model import ItemProperties, ParameterProperties

@dataclass
class ParameterGenerator(ParameterProperties):
    strategy: Optional[FieldConfiguration] = None
    _generator: Optional[RandomGenerator] = None 

    @property
    def generator(self):
        if self._generator is None and self.strategy:
            self._generator = RandomGeneratorFactory.create(self.strategy.type, **self.strategy.genParameters)
        return self._generator
    
    @classmethod
    def from_dict(cls, data: dict):
        # 1. Lấy danh sách các field mà class này (và cha nó) chấp nhận
        class_fields = {f.name for f in fields(cls)}
        
        # 2. Lọc dữ liệu đầu vào: Chỉ giữ lại key nào class có khai báo
        # Quan trọng: Tạm thời lấy 'schema' ra để xử lý riêng vì nó cần convert sang ItemProperties
        filtered_data = {
            k: v for k, v in data.items() 
            if k in class_fields and k != 'schema'
        }
        # 3. Khởi tạo instance
        # Lúc này filtered_data đã có 'name' (nếu trong data có 'name') 
        # và vì 'name' nằm trong class_fields nên sẽ không bị lỗi nữa.
        instance = cls(**filtered_data)
        
        # 4. Xử lý logic gán schema (nested conversion)
        raw_schema = data.get('schema')
        if raw_schema:
            # Nếu raw_schema là dict, convert nó, nếu đã là ItemProperties thì giữ nguyên
            if isinstance(raw_schema, dict):
                instance.schema = ItemProperties.from_dict(raw_schema)
            else:
                instance.schema = raw_schema
                
        return instance
@dataclass
class ItemGenerator(ItemProperties):
    strategy: Optional[FieldConfiguration] = None
    _generator: Optional[RandomGenerator] = None 
    
    @property
    def generator(self):
        if self._generator is None and self.strategy:
            self._generator = RandomGeneratorFactory.create(self.strategy.type, **self.strategy.genParameters)
        return self._generator
    

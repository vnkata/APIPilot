from common.logger import get_logger, LogLevel
from pydantic import BaseModel
from typing import List

print(__file__)
logger = get_logger(name="logger_examples")

logger.info("This is an info message.", user="alice", action="login")
logger.debug("This is a debug message.")


class Product(BaseModel):
    id: int
    name: str
    price: float
    category: List[str] = []


product = Product(
    id=1, name="Laptop", price=999.99, category=["Electronics", "Computers"]
)
logger.info("Product created", product=product)

logger.info("Integer array", data=[1, 2, 3, 4, 5])

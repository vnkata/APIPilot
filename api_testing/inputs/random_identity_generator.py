from faker import Faker
from .random_generator import RandomGenerator

class RandomIdentityGenerator(RandomGenerator):
    """
    A generator that produces random identity information (name, email, address, etc.).

    Attributes:
        field (str): The type of identity field to generate ('name', 'email', 'address', etc.).
    """
    description: str = """A generator that produces random identity information (name, email, address, etc.).

    Attributes:
        field (str): The type of identity field to generate ('name', 'email', 'address', etc.).
    """

    def __init__(self, field: str = "name", seed: int | None = None):
        super().__init__(seed)
        self.field = field
        self.fake = Faker()
        self._field_map = {
            "name": self.fake.name,
            "first_name": self.fake.first_name,
            "last_name": self.fake.last_name,
            "email": self.fake.email,
            "safe_email": self.fake.safe_email,
            "address": self.fake.address,
            "city": self.fake.city,
            "job": self.fake.job,
            "company": self.fake.company,
            "ssn": self.fake.ssn,
        }

    def next_value(self) -> str:
        if self.field not in self._field_map:
            raise ValueError(f"Unsupported identity field: {self.field}")
        return self._field_map[self.field]()
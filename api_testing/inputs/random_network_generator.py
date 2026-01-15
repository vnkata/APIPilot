from typing import Literal
from faker import Faker
from .random_generator import RandomGenerator

class RandomNetworkGenerator(RandomGenerator):
    """
    A generator that produces valid network-related identifiers such as IP addresses, 
    MAC addresses, URLs, and UUIDs.

    Attributes:
        mode (str): The type of network data to generate 
            ('ipv4', 'ipv6', 'mac', 'url', 'uuid', 'uri', 'email').
    """
    description: str = """A generator that produces valid network-related identifiers.
    Params:
        mode (str): The type of network data ('ipv4', 'ipv6', 'mac', 'url', 'uuid', 'uri', 'email').
    Output:
        str: The generated network identifier.
    """

    def __init__(
        self,
        mode: Literal["ipv4", "ipv6", "mac", "url", "uuid", "uri", "email"] = "ipv4",
        seed: int | None = None
    ):
        super().__init__(seed)
        self.mode = mode.lower()
        self.fake = Faker()

    def next_value(self) -> str:
        """Generate the next valid network value based on the selected mode."""
        mode_map = {
            "ipv4": self.fake.ipv4,
            "ipv6": self.fake.ipv6,
            "mac": self.fake.mac_address,
            "url": self.fake.url,
            "uuid": self.fake.uuid4,
            "uri": self.fake.uri,
            "email": self.fake.email,
        }

        if self.mode not in mode_map:
            raise ValueError(f"Unsupported network mode: {self.mode}")
            
        return str(mode_map[self.mode]())

    def next_value_as_string(self) -> str:
        """Return the value as a string (useful for all network types)."""
        return self.next_value()
    def next_fuzz_value(self, strategy: str):
        pass
from typing import Literal
from faker import Faker
from .random_generator import RandomGenerator

class RandomCreditCardGenerator(RandomGenerator):
    """
    A generator that produces valid credit card information, including numbers,
    expiry dates, and security codes (CVV).

    Attributes:
        card_type (str): The brand of card (e.g., 'visa', 'mastercard', 'amex').
    """
    description: str = """A generator that produces valid (Luhn-compliant) credit card data.
    Params:
        card_type (str): The card brand ('visa', 'mastercard', 'amex', 'discover', 'jcb').
    Output:
        str: Depending on the method called, returns card number, CVV, or expiry.
    """

    def __init__(
        self,
        card_type: Literal["visa", "mastercard", "amex", "discover", "jcb"] = "visa",
        seed: int | None = None
    ):
        super().__init__(seed)
        self.card_type = card_type.lower()
        self.fake = Faker()

    def next_value(self) -> str:
        """Returns a valid credit card number for the specified provider."""
        return self.fake.credit_card_number(card_type=self.card_type)

    def next_full_details(self) -> dict:
        """Returns a full dictionary of card details (Number, Expiry, CVV)."""
        return {
            "card_number": self.next_value(),
            "expiry_date": self.fake.credit_card_expire(),
            "security_code": self.fake.credit_card_security_code(card_type=self.card_type),
            "card_type": self.card_type
        }

    def next_value_as_string(self) -> str:
        return self.next_value()
    def next_fuzz_value(self, strategy: str):
        pass
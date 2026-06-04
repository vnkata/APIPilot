"""Unit tests for RandomCreditCardGenerator."""
import pytest
import re
from api_testing.inputs.random_credit_card_generator import RandomCreditCardGenerator


class TestRandomCreditCardGenerator:
    """Test suite for RandomCreditCardGenerator."""

    def test_initialization_default_visa(self):
        """Test default initialization is visa."""
        gen = RandomCreditCardGenerator()
        assert gen.card_type == "visa"

    def test_initialization_mastercard(self):
        """Test initialization with mastercard."""
        gen = RandomCreditCardGenerator(card_type="mastercard")
        assert gen.card_type == "mastercard"

    def test_initialization_amex(self):
        """Test initialization with amex."""
        gen = RandomCreditCardGenerator(card_type="amex")
        assert gen.card_type == "amex"

    def test_initialization_discover(self):
        """Test initialization with discover."""
        gen = RandomCreditCardGenerator(card_type="discover")
        assert gen.card_type == "discover"

    def test_initialization_jcb(self):
        """Test initialization with jcb."""
        gen = RandomCreditCardGenerator(card_type="jcb")
        assert gen.card_type == "jcb"

    def test_initialization_with_seed(self):
        """Test that seed is accepted."""
        gen = RandomCreditCardGenerator(seed=12345)
        assert gen.get_seed() == 12345

    def test_next_value_returns_string(self):
        """Test that next_value returns a string."""
        gen = RandomCreditCardGenerator(seed=42)
        for _ in range(5):
            value = gen.next_value()
            assert isinstance(value, str)

    def test_next_value_visa_format(self):
        """Test visa card number starts with 4."""
        gen = RandomCreditCardGenerator(card_type="visa", seed=42)
        for _ in range(5):
            value = gen.next_value()
            # Remove spaces and dashes
            clean = value.replace(" ", "").replace("-", "")
            assert clean.startswith("4"), f"Visa should start with 4: {value}"

    def test_next_value_mastercard_format(self):
        """Test mastercard number starts with 5 or 2."""
        gen = RandomCreditCardGenerator(card_type="mastercard", seed=42)
        for _ in range(5):
            value = gen.next_value()
            clean = value.replace(" ", "").replace("-", "")
            assert clean[0] in ["5", "2"], f"MasterCard should start with 5 or 2: {value}"

    def test_next_value_amex_format(self):
        """Test amex card number starts with 3."""
        gen = RandomCreditCardGenerator(card_type="amex", seed=42)
        for _ in range(5):
            value = gen.next_value()
            clean = value.replace(" ", "").replace("-", "")
            assert clean.startswith("3"), f"Amex should start with 3: {value}"

    def test_next_value_only_digits(self):
        """Test that card numbers contain only digits and separators."""
        gen = RandomCreditCardGenerator(seed=42)
        for _ in range(10):
            value = gen.next_value()
            clean = value.replace(" ", "").replace("-", "")
            assert clean.isdigit(), f"Card number should be digits only: {value}"

    def test_next_full_details_returns_dict(self):
        """Test that next_full_details returns a dictionary."""
        gen = RandomCreditCardGenerator(seed=42)
        details = gen.next_full_details()
        
        assert isinstance(details, dict)
        assert "card_number" in details
        assert "expiry_date" in details
        assert "security_code" in details
        assert "card_type" in details

    def test_next_full_details_card_number(self):
        """Test that full details contains valid card number."""
        gen = RandomCreditCardGenerator(card_type="visa", seed=42)
        details = gen.next_full_details()
        
        assert isinstance(details["card_number"], str)
        clean = details["card_number"].replace(" ", "").replace("-", "")
        assert len(clean) >= 13

    def test_next_full_details_expiry_date(self):
        """Test that full details contains expiry date."""
        gen = RandomCreditCardGenerator(seed=42)
        details = gen.next_full_details()
        
        assert isinstance(details["expiry_date"], str)
        # Expiry is usually in MM/YY format
        assert len(details["expiry_date"]) >= 4

    def test_next_full_details_security_code(self):
        """Test that full details contains security code."""
        gen = RandomCreditCardGenerator(seed=42)
        details = gen.next_full_details()
        
        cvv = details["security_code"]
        assert isinstance(cvv, str)
        # CVV should be 3 or 4 digits
        assert cvv.isdigit()
        assert 3 <= len(cvv) <= 4

    def test_next_full_details_card_type(self):
        """Test that full details contains card type."""
        gen = RandomCreditCardGenerator(card_type="mastercard", seed=42)
        details = gen.next_full_details()
        
        assert details["card_type"] == "mastercard"

    def test_next_value_as_string(self):
        """Test that next_value_as_string returns string."""
        gen = RandomCreditCardGenerator(seed=42)
        value = gen.next_value_as_string()
        assert isinstance(value, str)

    def test_case_insensitive_card_type(self):
        """Test that card type is case-insensitive."""
        gen1 = RandomCreditCardGenerator(card_type="VISA")
        gen2 = RandomCreditCardGenerator(card_type="MasterCard")
        
        assert gen1.card_type == "visa"
        assert gen2.card_type == "mastercard"

    def test_description_exists(self):
        """Test that description attribute exists."""
        gen = RandomCreditCardGenerator()
        assert gen.description is not None
        assert len(gen.description) > 0

    def test_luhn_validity(self):
        """Test that generated card numbers pass Luhn algorithm."""
        def luhn_check(card_number: str) -> bool:
            """Validate card number using Luhn algorithm."""
            clean = card_number.replace(" ", "").replace("-", "")
            digits = [int(d) for d in clean]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            
            checksum = sum(odd_digits)
            for d in even_digits:
                d *= 2
                if d > 9:
                    d -= 9
                checksum += d
            
            return checksum % 10 == 0
        
        gen = RandomCreditCardGenerator(seed=42)
        for _ in range(10):
            value = gen.next_value()
            assert luhn_check(value), f"Card number failed Luhn check: {value}"

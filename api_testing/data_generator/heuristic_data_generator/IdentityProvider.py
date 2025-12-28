from faker import Faker
from typing import Optional, Any

from api_testing.data_generator.heuristic_data_generator.BaseProvider import BaseProvider


class IdentityProvider(BaseProvider):
    """
    Provider for personal and professional identity data.
    All methods return strings unless specified otherwise.
    """
    def __init__(self, faker_instance: Faker):
        self.fake = faker_instance

    def name(self) -> str:
        """
        Returns a full person name. 
        Example: 'John Doe'
        """
        return self.fake.name()

    def first_name(self) -> str:
        """
        Returns a random first name.
        Example: 'John'
        """
        return self.fake.first_name()

    def last_name(self) -> str:
        """
        Returns a random last name.
        Example: 'Doe'
        """
        return self.fake.last_name()

    def email(self) -> str:
        """
        Returns a random email address.
        Example: 'jdoe@example.com'
        """
        return self.fake.email()

    def safe_email(self) -> str:
        """
        Returns a test-safe email address ending in .example or .test.
        Example: 'user1@example.test'
        """
        return self.fake.safe_email()

    def address(self) -> str:
        """
        Returns a complete multi-line mailing address.
        Includes street, city, state, and zip code.
        """
        return self.fake.address()

    def city(self) -> str:
        """
        Returns a random city name.
        """
        return self.fake.city()

    def dob(self, minimum_age: int = 18, maximum_age: int = 65) -> str:
        """
        Generates a date of birth string based on an age range.
        
        :param minimum_age: Minimum age of the person (default: 18).
        :param maximum_age: Maximum age of the person (default: 65).
        :return: ISO-8601 formatted date string (YYYY-MM-DD).
        """
        date_obj = self.fake.date_of_birth(minimum_age=minimum_age, maximum_age=maximum_age)
        return date_obj.strftime("%Y-%m-%d")

    def job(self) -> str:
        """
        Returns a random professional job title.
        Example: 'Software Engineer'
        """
        return self.fake.job()

    def company(self) -> str:
        """
        Returns a random company name.
        Example: 'Acme Corp'
        """
        return self.fake.company()

    def ssn(self) -> str:
        """
        Generates a random Social Security Number.
        Useful for unique identification fields.
        """
        return self.fake.ssn()
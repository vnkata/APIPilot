from faker import Faker

from api_testing.data_generator.heuristic_data_generator.BaseProvider import BaseProvider


class LoremProvider(BaseProvider):
    """
    Provider for generating random placeholder text (Lorem Ipsum).
    Useful for testing descriptions, comments, or any unstructured text fields.
    """
    def __init__(self, faker_instance: Faker):
        self.fake = faker_instance

    def word(self) -> str:
        """
        Generates a single random word.
        Example: 'aut'
        """
        return self.fake.word()

    def sentence(self, nb_words: int = 6) -> str:
        """
        Generates a single random sentence.
        
        :param nb_words: Number of words in the sentence (default: 6).
        :return: A capitalized string ending with a period.
        """
        return self.fake.sentence(nb_words=nb_words)

    def paragraph(self, nb_sentences: int = 3) -> str:
        """
        Generates a single random paragraph.
        
        :param nb_sentences: Number of sentences in the paragraph (default: 3).
        :return: A block of text containing multiple sentences.
        """
        return self.fake.paragraph(nb_sentences=nb_sentences)
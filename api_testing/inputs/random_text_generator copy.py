import os
import sys
import warnings
import string
import re
from typing import Any, Literal

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator
from hypothesis import strategies as st
from hypothesis.errors import NonInteractiveExampleWarning

# Tắt cảnh báo chạy .example() của Hypothesis
warnings.filterwarnings("ignore", category=NonInteractiveExampleWarning)


class RandomTextGenerator(RandomGenerator):
    """
    A generator that produces random text using the 'lorem' provider from Faker.

    Attributes:
        mode (str): The type of text to generate ('word', 'sentence', 'paragraph').
        count (int): Number of items to generate.
    """
    description: str = """
    Generates random text according to the specified mode.
    Attributes:
        mode (str): Generation mode — can be "word", "sentence", "paragraph", or "regex".
        pattern (str): Regular expression pattern used when mode is "regex". using it for phone, currency,lang,...
        count (int): Number of words, sentences, or paragraphs to generate based on the mode.
        seed (int | N  one): Optional random seed value to ensure reproducible results.
    """

    def __init__(
        self,
        mode: Literal["word", "sentence", "paragraph","regex"] = "sentence",
        pattern: str = None,
        count: int = 1,
        seed: int | None = None
    ):
        super().__init__(seed)
        self.mode = mode
        self.count = count
        self.pattern = pattern
        # self.fake = Faker()

    def next_value(self, *args, **kargs) -> str:
        # Định nghĩa strategy tạo một từ ngẫu nhiên (chữ cái thường từ a-z, độ dài từ 2 đến 10 ký tự)
        word_st = st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=10)

        if self.mode == "word":
            words_strategy = st.lists(word_st, min_size=self.count, max_size=self.count).map(
                lambda w: " ".join(w)
            )
            return words_strategy.example()

        elif self.mode == "sentence":
            single_sentence_st = st.lists(word_st, min_size=5, max_size=12).map(
                lambda w: " ".join(w).capitalize() + "."
            )
            sentences_strategy = st.lists(single_sentence_st, min_size=self.count, max_size=self.count).map(
                lambda s: " ".join(s)
            )
            return sentences_strategy.example()

        elif self.mode == "paragraph":
            # Định nghĩa cấu trúc câu tươngtự như trên
            single_sentence_st = st.lists(word_st, min_size=5, max_size=12).map(
                lambda w: " ".join(w).capitalize() + "."
            )
            single_paragraph_st = st.lists(single_sentence_st, min_size=3, max_size=6).map(
                lambda s: " ".join(s)
            )
            # Tạo đúng `self.count` đoạn văn và nối với nhau bằng dấu xuống dòng kép `\n\n`
            paragraphs_strategy = st.lists(single_paragraph_st, min_size=self.count, max_size=self.count).map(
                lambda p: "\n\n".join(p)
            )
            return paragraphs_strategy.example()

        elif self.mode == "regex":
            rex = st.from_regex(re.compile(self.pattern, flags=re.ASCII), fullmatch=True).example()
            return rex
            
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
    # def next_value(self, *args, **kargs) -> str:
    #     if self.mode == "word":
    #         return " ".join(self.fake.words(self.count))
    #     elif self.mode == "sentence":
    #         return " ".join(self.fake.sentences(self.count))
    #     elif self.mode == "paragraph":
    #         return "\n\n".join(self.fake.paragraphs(self.count))
    #     elif self.mode == "regex":
    #         rex = st.from_regex(re.compile(self.pattern,flags=re.ASCII), fullmatch=True).example()
    #         return rex
    #     else:
    #         raise ValueError(f"Unsupported mode: {self.mode}")
        
    def next_fuzz_value(self, *args, **kargs) -> Any:
        return self.next_value(*args, **kargs)
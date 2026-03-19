import csv
import os
from typing import Any, List
from .random_generator import RandomGenerator

class FileSourceGenerator(RandomGenerator): 
    """
    A generator that loads data from an external CSV file.
    This helps manage large datasets outside of the main configuration file.
    """
    description: str = """Loads data from a CSV file and randomly selects values.
    Attributes:
        file_path (str): The path to the data file.
        data_key (str): Specific column name to retrieve data from (optional).
        count (int): Number of values to select at once.
    """

    def __init__(
        self,
        file_path: str,
        data_key: str | None = None,
        count: int = 1,
        seed: int | None = None
    ):
        super().__init__(seed)
        self.file_path = file_path
        self.data_key = data_key
        self.count = count
        self.values: List[Any] = self._load_file()

    def _load_file(self) -> List[Any]:
        """Loads and parses the file structure."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found at: {self.file_path}")

        try:
            return self._parse_csv()
        except Exception as e:
            raise RuntimeError(f"Error processing file {self.file_path}: {str(e)}")

    def _parse_csv(self) -> List[Any]:
        """Parses the CSV file content."""
        data = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f) if self.data_key else csv.reader(f)
            for row in reader:
                if self.data_key:
                    data.append(row.get(self.data_key))
                else:
                    data.append(row)
        return data

    def next_value(self) -> Any:
        """Randomly selects a value from the loaded data."""
        if not self.values:
            return None
        
        if self.count <= 1:
            return self.rand.choice(self.values)
        
        return self.rand.sample(self.values, min(self.count, len(self.values)))
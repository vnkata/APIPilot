"""CSV management utilities for Beet."""

import csv
import os
from typing import List, Dict, Optional
from . import file_manager


def read_csv(path: str, delimiter: str = ',', include_first_row: bool = True) -> List[List[str]]:
    """Read CSV file.
    
    Args:
        path: Path to CSV file
        delimiter: CSV delimiter character
        include_first_row: Whether to include header row
        
    Returns:
        List of rows, each row is a list of strings
    """
    rows = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                rows.append(row)
    except IOError as e:
        print(f"Error parsing CSV file: {path}")
        print(f"Exception: {e}")
    
    if not include_first_row and rows:
        rows.pop(0)
    
    return rows


def read_values(path: str) -> List[str]:
    """Read first column values from CSV file.
    
    Args:
        path: Path to CSV file
        
    Returns:
        List of values from first column
    """
    values = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    values.append(row[0])
    except IOError as e:
        print(f"Error parsing CSV file: {path}")
        print(f"Exception: {e}")
    
    return values


def get_csv_record(line: str) -> Optional[List[str]]:
    """Parse a single CSV line.
    
    Args:
        line: CSV line as string
        
    Returns:
        Parsed record as list of strings, or None if error
    """
    try:
        reader = csv.reader([line])
        records = list(reader)
        if len(records) != 1:
            raise IndexError("Each line should contain only one record")
        return records[0]
    except IOError as e:
        print("Error parsing CSV file")
        print(f"Exception: {e}")
        return None


def create_csv_with_header(path: str, header: str) -> None:
    """Create CSV file with header.
    
    Args:
        path: Path to CSV file
        header: Header row
    """
    file_manager.delete_file(path)
    file_manager.create_file_if_not_exists(path)
    write_csv_row(path, header)


def write_csv_row(path: str, row: str) -> None:
    """Append a row to CSV file.
    
    Args:
        path: Path to CSV file
        row: Row as string
    """
    try:
        with open(path, 'a', encoding='utf-8', newline='') as f:
            f.write(row + '\n')
    except IOError as e:
        print(f"The line could not be written to the CSV: {path}")
        print(f"Exception: {e}")

"""File management utilities for Beet."""

import os
from pathlib import Path
from typing import Optional


def write_file(filepath: str, content: str) -> None:
    """Write content to a file.
    
    Args:
        filepath: Path to the file
        content: Content to write
    """
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully wrote to the file.")
    except IOError as e:
        print(f"An error occurred: {e}")


def read_file_as_string(path: str) -> str:
    """Read file content as string.
    
    Args:
        path: Path to the file
        
    Returns:
        File content as string
    """
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def delete_file(path: str) -> bool:
    """Delete a file.
    
    Args:
        path: Path to the file
        
    Returns:
        True if deleted, False otherwise
    """
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def check_if_exists(path: str) -> bool:
    """Check if a file exists.
    
    Args:
        path: Path to the file
        
    Returns:
        True if exists, False otherwise
    """
    return os.path.exists(path)


def create_file_if_not_exists(path: str) -> bool:
    """Create a file if it doesn't exist.
    
    Args:
        path: Path to the file
        
    Returns:
        True if created, False if already exists
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(path):
            Path(path).touch()
            return True
        return False
    except IOError as e:
        print(f"Exception: {e}")
        return False

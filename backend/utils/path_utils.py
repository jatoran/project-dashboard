"""
Path utilities for the Project Dashboard.
Simplified for native Windows execution.
"""
from pathlib import Path


def normalize_path(path_str: str) -> str:
    """
    Normalize a path string for consistent handling.
    Converts forward slashes to backslashes on Windows and resolves the path.
    """
    path = Path(path_str)
    return str(path.resolve())


def resolve_path_case(path_str: str) -> str:
    """
    Resolves the actual case-sensitive path on the filesystem for a given path string.

    On Windows, filesystem is case-insensitive but case-preserving, so we
    resolve to the actual stored case for consistency.

    Simplified: just use resolve() which handles this on modern Windows/Python.
    """
    path = Path(path_str)
    try:
        if path.exists():
            return str(path.resolve())
    except (OSError, PermissionError):
        pass
    return path_str

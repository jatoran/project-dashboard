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
    Useful when the input might have wrong casing (e.g. 'Projects' vs 'projects').
    
    On Windows, filesystem is case-insensitive but case-preserving, so we
    resolve to the actual stored case for consistency.
    """
    # If path exists as-is, resolve it to get canonical form
    path = Path(path_str)
    if path.exists():
        return str(path.resolve())
    
    # Try to resolve case-insensitively by walking the path
    parts = path.parts
    if not parts:
        return path_str
    
    # Start from the root/drive
    current_path = Path(parts[0])
    
    for part in parts[1:]:
        if not current_path.exists():
            # Can't continue, return original
            return path_str
        
        # Look for case-insensitive match in current directory
        found = False
        try:
            for item in current_path.iterdir():
                if item.name.lower() == part.lower():
                    current_path = item
                    found = True
                    break
        except (OSError, PermissionError):
            return path_str
        
        if not found:
            # Component not found, return original
            return path_str
    
    return str(current_path)
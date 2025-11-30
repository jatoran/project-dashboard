import re

def windows_to_linux(win_path: str) -> str:
    """
    Converts a Windows path (e.g., 'D:\Projects\MyApp' or 'D:/Projects/MyApp') 
    to a WSL/Linux path (e.g., '/mnt/d/Projects/MyApp').
    """
    # Normalize separators to forward slashes
    path = win_path.replace('\\', '/')
    
    # Handle drive letter (e.g. "C:", "C:/", "c:/")
    # Regex explanation:
    # ^([a-zA-Z]):   -> Starts with single letter and colon (Group 1: drive)
    # (?:/)?         -> Non-capturing group, optional forward slash
    # (.*)           -> The rest of the path (Group 2: path)
    match = re.match(r'^([a-zA-Z]):(?:/)?(.*)', path)
    
    if match:
        drive = match.group(1).lower()
        rest = match.group(2)
        
        # Ensure we don't have double slashes if 'rest' started with one (though replace handled it)
        if rest.startswith('/'):
            rest = rest.lstrip('/')
            
        return f"/mnt/{drive}/{rest}"
        
    return path

def linux_to_windows(linux_path: str) -> str:
    """
    Converts a WSL/Linux path (e.g., '/mnt/d/Projects/MyApp') 
    to a Windows path (e.g., 'D:\\Projects\\MyApp').
    """
    # Check for /mnt/x/ pattern
    match = re.match(r'^/mnt/([a-z])/(.*)', linux_path)
    if match:
        drive = match.group(1).upper()
        rest = match.group(2)
        # Convert forward slashes back to backslashes for Windows
        rest_win = rest.replace('/', '\\')
        return f"{drive}:\\{rest_win}"
        
    # Fallback: check for /mnt/x (root of drive)
    match_root = re.match(r'^/mnt/([a-z])/?$', linux_path)
    if match_root:
        drive = match_root.group(1).upper()
        return f"{drive}:\\"

    return linux_path

def resolve_path_case(path_str: str) -> str:
    """
    Resolves the actual case-sensitive path on the filesystem for a given path string.
    Useful when the input might have wrong casing (e.g. 'Projects' vs 'projects').
    """
    import os
    
    # If path exists as-is, return it
    if os.path.exists(path_str):
        return path_str
        
    # Split path into parts
    parts = path_str.strip('/').split('/')
    
    # Handle absolute path starting with /
    current_path = '/' if path_str.startswith('/') else '.'
    
    # If strictly relative (no leading /), start from current dir
    # But our converted paths from windows_to_linux usually start with /mnt/...
    
    for part in parts:
        if not part: continue # Skip empty parts from double slashes
        
        # Check if 'part' exists in 'current_path'
        next_path = os.path.join(current_path, part)
        if os.path.exists(next_path):
            current_path = next_path
            continue
            
        # If not, search directory for case-insensitive match
        found = False
        try:
            for item in os.listdir(current_path):
                if item.lower() == part.lower():
                    current_path = os.path.join(current_path, item)
                    found = True
                    break
        except OSError:
            # If current_path is not a dir or permission denied, stop and return built path so far + rest
            # This allows the scanner to fail with a "Path not found" later
            return path_str 
            
        if not found:
            # Component not found even case-insensitively.
            # Return the original path (or what we have so far + rest)
            # so the caller can handle the 'not found' error.
            return path_str
            
    return current_path
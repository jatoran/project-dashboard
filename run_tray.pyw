#!/usr/bin/env python
"""
Launch the Project Dashboard system tray application.
Uses .pyw extension to hide console window on Windows.

This script uses uv to run the tray application with the correct dependencies.
"""
import subprocess
import sys
from pathlib import Path

def main():
    # Get the project root directory
    project_dir = Path(__file__).parent
    
    # Run the tray app using uv to ensure dependencies are available
    subprocess.run(
        ["uv", "run", "--project", "backend", "python", "-m", "backend.tray"],
        cwd=str(project_dir),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

if __name__ == "__main__":
    main()

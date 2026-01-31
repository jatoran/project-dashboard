"""
Launcher service - opens projects in VS Code or terminal.
Simplified for native Windows execution (no host agent required).
"""
import subprocess
import os
import shutil
from pathlib import Path
from fastapi import HTTPException


class Launcher:
    """Launches VS Code, terminals, and other tools for projects."""

    # Cache for code command path (found once, reused)
    _code_cmd_cache: str = None
    _wt_available: bool = None

    def launch(self, path: str, launch_type: str):
        """
        Launch a project in the specified way.

        Args:
            path: Path to the project (Windows path)
            launch_type: 'vscode', 'terminal', or 'explorer'
        """
        project_path = Path(path)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")

        try:
            if launch_type == "vscode":
                self._launch_vscode(project_path)
            elif launch_type == "vscode_workspace":
                self._launch_vscode_workspace(project_path)
            elif launch_type == "terminal":
                self._launch_terminal(project_path)
            elif launch_type == "explorer":
                self._launch_explorer(project_path)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown launch type: {launch_type}")
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Launch failed: {e}")
    
    def _launch_vscode(self, path: Path):
        """Open VS Code at the given path."""
        code_cmd = self._find_code_cmd()
        subprocess.Popen(
            [code_cmd, str(path)],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _launch_vscode_workspace(self, workspace_file: Path):
        """Open a VS Code workspace file."""
        code_cmd = self._find_code_cmd()
        subprocess.Popen(
            [code_cmd, str(workspace_file)],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _launch_terminal(self, path: Path):
        """Open a terminal at the given path."""
        # Check Windows Terminal availability (cached)
        if Launcher._wt_available is None:
            wt_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")
            Launcher._wt_available = os.path.exists(wt_path)

        if Launcher._wt_available:
            subprocess.Popen(["wt", "-d", str(path)])
        else:
            subprocess.Popen(f'start cmd /k "cd /d {path}"', shell=True)

    def _launch_explorer(self, path: Path):
        """Open File Explorer at the given path."""
        subprocess.Popen(["explorer", str(path)])

    def _find_code_cmd(self) -> str:
        """Find the VS Code command (cached for speed)."""
        # Return cached result
        if Launcher._code_cmd_cache is not None:
            return Launcher._code_cmd_cache

        # Try 'code' command first using shutil.which (fast, no shell)
        code_path = shutil.which("code")
        if code_path:
            Launcher._code_cmd_cache = code_path
            return code_path

        # Common VS Code installation paths
        common_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft VS Code\bin\code.cmd"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft VS Code\bin\code.cmd"),
        ]

        for code_path in common_paths:
            if os.path.exists(code_path):
                Launcher._code_cmd_cache = code_path
                return code_path

        raise FileNotFoundError("VS Code not found. Please install it or add 'code' to PATH.")

"""
Launcher service - opens projects in VS Code or terminal.
Simplified for native Windows execution (no host agent required).
"""
import subprocess
import os
from pathlib import Path
from fastapi import HTTPException


class Launcher:
    """Launches VS Code, terminals, and other tools for projects."""
    
    def launch(self, path: str, launch_type: str):
        """
        Launch a project in the specified way.
        
        Args:
            path: Path to the project (Windows path)
            launch_type: 'vscode', 'terminal', or 'explorer'
        """
        # Normalize path
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
                
            print(f"Launched {launch_type} for: {path}")
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Launch failed: {e}")
    
    def _launch_vscode(self, path: Path):
        """Open VS Code at the given path."""
        code_cmd = self._find_code_cmd()
        subprocess.Popen([code_cmd, str(path)], shell=True)
    
    def _launch_vscode_workspace(self, workspace_file: Path):
        """Open a VS Code workspace file."""
        code_cmd = self._find_code_cmd()
        subprocess.Popen([code_cmd, str(workspace_file)], shell=True)
    
    def _launch_terminal(self, path: Path):
        """Open a terminal at the given path."""
        # Use Windows Terminal if available, fall back to cmd
        if os.path.exists(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")):
            subprocess.Popen(["wt", "-d", str(path)], shell=True)
        else:
            subprocess.Popen(f'start cmd /k "cd /d {path}"', shell=True)
    
    def _launch_explorer(self, path: Path):
        """Open File Explorer at the given path."""
        subprocess.Popen(["explorer", str(path)], shell=True)
    
    def _find_code_cmd(self) -> str:
        """Find the VS Code command."""
        # Try 'code' command first (typically in PATH)
        if os.system("where code >nul 2>&1") == 0:
            return "code"
        
        # Common VS Code installation paths
        common_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft VS Code\bin\code.cmd"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft VS Code\bin\code.cmd"),
        ]
        
        for code_path in common_paths:
            if os.path.exists(code_path):
                return code_path
        
        raise FileNotFoundError("VS Code not found. Please install it or add 'code' to PATH.")

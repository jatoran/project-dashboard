"""
Launcher service - opens projects in VS Code, terminal, or other tools.
Supports dynamic launchers from configuration.
"""
import subprocess
import os
import sys
import shutil
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

from .config import get_config

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform == "darwin"


class Launcher:
    """Launches VS Code, terminals, and other tools for projects."""

    # Cache for code command path (found once, reused)
    _code_cmd_cache: str = None
    _wt_available: bool = None

    def launch(self, path: str, launch_type: str):
        """
        Launch a project in the specified way.

        Args:
            path: Path to the project
            launch_type: Launcher ID (e.g., 'vscode', 'terminal', 'claude')
        """
        project_path = Path(path)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")

        config = get_config()

        try:
            # Check if it's a builtin launcher
            launcher = config.get_launcher_by_id(launch_type)

            if launcher:
                command = launcher.get("command", "")
                is_builtin = launcher.get("builtin", False)

                if is_builtin:
                    # Handle builtin commands
                    if command == "__vscode__":
                        self._launch_vscode(project_path)
                    elif command == "__terminal__":
                        self._launch_terminal(project_path)
                    elif command == "__explorer__":
                        self._launch_explorer(project_path)
                    else:
                        raise HTTPException(status_code=400, detail=f"Unknown builtin command: {command}")
                else:
                    # Custom command - run in terminal
                    self._launch_cli_tool(project_path, command)
            else:
                # Fallback for legacy launch types (backwards compatibility)
                if launch_type == "vscode":
                    self._launch_vscode(project_path)
                elif launch_type == "vscode_workspace":
                    self._launch_vscode_workspace(project_path)
                elif launch_type == "terminal":
                    self._launch_terminal(project_path)
                elif launch_type == "explorer":
                    self._launch_explorer(project_path)
                elif launch_type in ("claude", "codex", "opencode"):
                    self._launch_cli_tool(project_path, launch_type)
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown launch type: {launch_type}")

        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Launch failed: {e}")

    def _launch_vscode(self, path: Path):
        """Open VS Code at the given path."""
        code_cmd = self._find_code_cmd()
        if IS_WINDOWS:
            subprocess.Popen(
                [code_cmd, str(path)],
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            subprocess.Popen([code_cmd, str(path)], shell=False)

    def _launch_vscode_workspace(self, workspace_file: Path):
        """Open a VS Code workspace file."""
        code_cmd = self._find_code_cmd()
        if IS_WINDOWS:
            subprocess.Popen(
                [code_cmd, str(workspace_file)],
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            subprocess.Popen([code_cmd, str(workspace_file)], shell=False)

    def _launch_terminal(self, path: Path, command: Optional[str] = None):
        """Open a terminal at the given path, optionally running a command."""
        if IS_WINDOWS:
            self._launch_terminal_windows(path, command)
        elif IS_LINUX:
            self._launch_terminal_linux(path, command)
        elif IS_MAC:
            self._launch_terminal_mac(path, command)
        else:
            raise HTTPException(status_code=500, detail=f"Unsupported platform: {sys.platform}")

    def _launch_terminal_windows(self, path: Path, command: Optional[str] = None):
        """Launch terminal on Windows."""
        # Check Windows Terminal availability (cached)
        if Launcher._wt_available is None:
            wt_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")
            Launcher._wt_available = os.path.exists(wt_path)

        if Launcher._wt_available:
            if command:
                subprocess.Popen(["wt", "-d", str(path), "cmd", "/k", command])
            else:
                subprocess.Popen(["wt", "-d", str(path)])
        else:
            if command:
                subprocess.Popen(f'start cmd /k "cd /d {path} && {command}"', shell=True)
            else:
                subprocess.Popen(f'start cmd /k "cd /d {path}"', shell=True)

    def _launch_terminal_linux(self, path: Path, command: Optional[str] = None):
        """Launch terminal on Linux."""
        # Try common terminal emulators
        terminals = [
            ("x-terminal-emulator", lambda p, c: ["x-terminal-emulator", "--working-directory", str(p)] + (["--", "bash", "-c", f"{c}; exec bash"] if c else [])),
            ("gnome-terminal", lambda p, c: ["gnome-terminal", "--working-directory", str(p)] + (["--", "bash", "-c", f"{c}; exec bash"] if c else [])),
            ("konsole", lambda p, c: ["konsole", "--workdir", str(p)] + (["-e", "bash", "-c", f"{c}; exec bash"] if c else [])),
            ("xfce4-terminal", lambda p, c: ["xfce4-terminal", "--working-directory", str(p)] + (["-e", f"bash -c '{c}; exec bash'"] if c else [])),
            ("xterm", lambda p, c: ["xterm", "-e", f"cd {p} && {c}; bash"] if c else ["xterm", "-e", f"cd {p} && bash"]),
        ]

        for term_name, args_builder in terminals:
            if shutil.which(term_name):
                args = args_builder(path, command)
                subprocess.Popen(args)
                return

        raise HTTPException(status_code=500, detail="No supported terminal emulator found")

    def _launch_terminal_mac(self, path: Path, command: Optional[str] = None):
        """Launch terminal on macOS."""
        if command:
            script = f'tell app "Terminal" to do script "cd {path} && {command}"'
        else:
            script = f'tell app "Terminal" to do script "cd {path}"'
        subprocess.Popen(["osascript", "-e", script])

    def _launch_explorer(self, path: Path):
        """Open file manager at the given path."""
        config = get_config()
        custom_fm = config.config.file_manager

        if custom_fm:
            # Use custom file manager from config
            if os.path.exists(custom_fm):
                if IS_WINDOWS:
                    subprocess.Popen([custom_fm, str(path)])
                else:
                    subprocess.Popen([custom_fm, str(path)])
            else:
                raise HTTPException(status_code=404, detail=f"File manager not found: {custom_fm}")
        else:
            # Use system default
            if IS_WINDOWS:
                subprocess.Popen(["explorer", str(path)])
            elif IS_LINUX:
                subprocess.Popen(["xdg-open", str(path)])
            elif IS_MAC:
                subprocess.Popen(["open", str(path)])
            else:
                raise HTTPException(status_code=500, detail=f"Unsupported platform: {sys.platform}")

    def _launch_cli_tool(self, path: Path, tool: str):
        """Open terminal at path and run a CLI tool."""
        self._launch_terminal(path, command=tool)

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

        if IS_WINDOWS:
            # Common VS Code installation paths on Windows
            common_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft VS Code\bin\code.cmd"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft VS Code\bin\code.cmd"),
            ]

            for code_path in common_paths:
                if os.path.exists(code_path):
                    Launcher._code_cmd_cache = code_path
                    return code_path

        elif IS_MAC:
            # Common VS Code paths on macOS
            mac_paths = [
                "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
                os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
            ]
            for code_path in mac_paths:
                if os.path.exists(code_path):
                    Launcher._code_cmd_cache = code_path
                    return code_path

        raise FileNotFoundError("VS Code not found. Please install it or add 'code' to PATH.")

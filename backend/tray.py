"""
System Tray Controller for Gemini Project Dashboard.
Provides a simple system tray icon to start/stop the server and open the dashboard.
"""
import subprocess
import sys
import time
import threading
import webbrowser
from pathlib import Path
from typing import Optional

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Missing dependencies. Install with: uv add pystray Pillow")
    sys.exit(1)

from .hotkey_manager import HotkeyManager
from .command_palette_ui import CommandPaletteUI


class DashboardTray:
    """System tray controller for the Project Dashboard."""
    
    PORT = 37453
    URL = f"http://localhost:{PORT}"
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.icon: Optional[pystray.Icon] = None
        self._running = False
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.palette_ui: Optional[CommandPaletteUI] = None
    
    def create_icon_image(self, running: bool = False) -> Image.Image:
        """Create a simple icon indicating server status."""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Background circle
        bg_color = (34, 197, 94) if running else (100, 100, 100)  # Green if running, gray if stopped
        draw.ellipse([4, 4, size-4, size-4], fill=bg_color)
        
        # Inner circle (dashboard icon representation)
        inner_color = (255, 255, 255)
        draw.ellipse([16, 16, size-16, size-16], fill=inner_color)
        
        # Small dot in center
        center_color = bg_color
        draw.ellipse([26, 26, size-26, size-26], fill=center_color)
        
        return image
    
    def update_icon(self):
        """Update the tray icon to reflect current state."""
        if self.icon:
            self.icon.icon = self.create_icon_image(self._running)
    
    def start_server(self, icon=None, item=None):
        """Start the uvicorn server."""
        if self._running:
            return
        
        # Get the project root directory  
        project_dir = Path(__file__).parent.parent
        
        # Start uvicorn via uv run to ensure dependencies are available
        self.server_process = subprocess.Popen(
            [
                "uv", "run", "--project", "backend",
                "uvicorn", "backend.main:app",
                "--host", "127.0.0.1",
                "--port", str(self.PORT),
            ],
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        
        self._running = True
        self.update_icon()
        print(f"Server started on {self.URL}")
    
    def stop_server(self, icon=None, item=None):
        """Stop the uvicorn server and all child processes."""
        if self.server_process:
            pid = self.server_process.pid
            
            # On Windows, we need to kill the entire process tree
            # because uv spawns child processes that don't get killed
            # when we terminate just the parent
            if sys.platform == "win32":
                try:
                    # taskkill /T kills the process tree, /F forces termination
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception as e:
                    print(f"Error killing process tree: {e}")
                    # Fallback to normal termination
                    self.server_process.terminate()
            else:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
            
            self.server_process = None
        
        self._running = False
        self.update_icon()
        print("Server stopped")
    
    def open_dashboard(self, icon=None, item=None):
        """Open the dashboard in the default browser."""
        if not self._running:
            # Auto-start if not running
            self.start_server()
            time.sleep(1)  # Give server time to start
        
        webbrowser.open(self.URL)
    
    def exit_app(self, icon=None, item=None):
        """Exit the application."""
        self.stop_server()
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        if self.icon:
            self.icon.stop()
    
    def open_command_palette(self, icon=None, item=None):
        """Open the command palette overlay."""
        if self.palette_ui:
            self.palette_ui.show()

    def create_menu(self):
        """Create the system tray menu."""
        def get_start_stop_text(item):
            return "Stop Server" if self._running else "Start Server"

        def toggle_server(icon, item):
            if self._running:
                self.stop_server()
            else:
                self.start_server()

        return pystray.Menu(
            pystray.MenuItem(
                get_start_stop_text,
                toggle_server,
            ),
            pystray.MenuItem(
                "Open Dashboard",
                self.open_dashboard,
                default=True,  # Double-click action
            ),
            pystray.MenuItem(
                "Command Palette (Win+Shift+W)",
                self.open_command_palette,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Exit",
                self.exit_app,
            ),
        )
    
    def run(self, autostart: bool = True):
        """Run the system tray application."""
        # Auto-start server on launch
        if autostart:
            self.start_server()

        # Create command palette UI (lightweight, stays hidden)
        print("Initializing command palette...")
        self.palette_ui = CommandPaletteUI()

        # Start global hotkey listener in background thread
        self.hotkey_manager = HotkeyManager(self.palette_ui)
        hotkey_thread = threading.Thread(
            target=self.hotkey_manager.start,
            daemon=True,
            name="HotkeyListener"
        )
        hotkey_thread.start()

        # Create and run the icon
        self.icon = pystray.Icon(
            "project-dashboard",
            self.create_icon_image(self._running),
            "Project Dashboard",
            menu=self.create_menu(),
        )

        print("✓ Command palette ready (instant show/hide)")
        print("Project Dashboard tray icon running...")
        print(f"Server: {self.URL}")
        print(f"Global Hotkey: Win+Shift+W")
        print("Right-click tray icon for options")

        self.icon.run()


def main():
    """Entry point for the tray application."""
    tray = DashboardTray()
    tray.run(autostart=True)


if __name__ == "__main__":
    main()

"""
Command Palette Launcher - Runs pywebview in its own process.
This is launched as a separate process so webview can use the main thread.
"""
import webview
from pathlib import Path
import time
import threading


class API:
    """JavaScript API for the command palette."""

    def __init__(self):
        self.window = None
        self.last_focus_time = time.time()
        self.checking_focus = False

    def close_window(self):
        """Close the command palette window."""
        if self.window:
            self.window.destroy()

    def check_focus_loop(self):
        """Background thread to check if window has lost focus."""
        while True:
            time.sleep(0.5)  # Check every 500ms
            if self.window and not self.checking_focus:
                try:
                    # Inject JS to check if window is focused
                    result = self.window.evaluate_js('document.hasFocus()')
                    if result is False:
                        # Window lost focus, close it
                        self.close_window()
                        break
                except:
                    pass  # Window might be closing


def main():
    """Launch the command palette window."""
    # Get the HTML file path
    html_path = Path(__file__).parent / "command_palette.html"

    # Create the API
    api = API()

    # Create window - smaller for faster loading
    window = webview.create_window(
        title="Command Palette",
        url=str(html_path),
        width=700,
        height=500,
        resizable=False,
        frameless=True,
        on_top=True,
        confirm_close=False,
        js_api=api,
        focus=True,  # Auto-focus when opened
    )

    api.window = window

    # Start focus checker in background thread
    def start_focus_checker():
        # Wait for window to be ready
        while not window.loaded:
            time.sleep(0.1)
        api.check_focus_loop()

    focus_thread = threading.Thread(target=start_focus_checker, daemon=True)
    focus_thread.start()

    # Start webview (blocking - runs on main thread)
    webview.start(debug=False)


if __name__ == "__main__":
    main()

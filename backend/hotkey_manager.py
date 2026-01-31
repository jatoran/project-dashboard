"""
Global Hotkey Manager for Command Palette.
Listens for Win+Shift+W and displays the command palette overlay.
"""
import threading
from pynput import keyboard
import time


class HotkeyManager:
    """Manages global hotkeys and command palette window."""

    def __init__(self, palette_ui=None):
        self.listener = None
        self.current_keys = set()
        self._last_launch = 0
        self._launch_cooldown = 0.3  # Prevent rapid re-launches
        self.palette_ui = palette_ui  # Reference to the UI

    def set_palette_ui(self, palette_ui):
        """Set the command palette UI instance."""
        self.palette_ui = palette_ui

    def show_command_palette(self):
        """Show the command palette (instant - just unhide window)."""
        # Cooldown to prevent rapid re-launches
        now = time.time()
        if now - self._last_launch < self._launch_cooldown:
            return
        self._last_launch = now

        # Show the pre-existing window (instant!)
        if self.palette_ui:
            try:
                self.palette_ui.show()
            except Exception as e:
                print(f"Failed to show command palette: {e}")

    def _on_press(self, key):
        """Handle key press events."""
        try:
            # Track pressed keys
            self.current_keys.add(key)

            # Check for Win+Shift+W combination
            # pynput uses different key representations
            has_win = (
                keyboard.Key.cmd in self.current_keys or  # Left Win
                keyboard.Key.cmd_r in self.current_keys   # Right Win
            )
            has_shift = (
                keyboard.Key.shift in self.current_keys or
                keyboard.Key.shift_r in self.current_keys
            )

            # Check for W key - can be either a string 'w'/'W' or a key object
            has_w = False
            if isinstance(key, str):
                # Key is a character string
                has_w = key.lower() == 'w'
            elif hasattr(key, 'char'):
                # Key is a key object with char attribute
                has_w = key.char and key.char.lower() == 'w'

            if has_win and has_shift and has_w:
                # Trigger command palette (instant show/hide)
                threading.Thread(target=self.show_command_palette, daemon=True).start()

        except Exception as e:
            pass  # Ignore errors to prevent crashes

    def _on_release(self, key):
        """Handle key release events."""
        try:
            # Remove released key from tracking
            if key in self.current_keys:
                self.current_keys.remove(key)
        except:
            pass

    def start(self):
        """Start the hotkey listener."""
        print("✓ Global hotkey registered: Win+Shift+W")
        print("  Press Win+Shift+W from anywhere to open command palette")

        # Start the keyboard listener (non-blocking)
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()

        # Keep thread alive (this doesn't block like keyboard.wait())
        # The listener runs in its own thread
        while self.listener.running:
            time.sleep(1)

    def stop(self):
        """Stop the hotkey listener."""
        try:
            if self.listener:
                self.listener.stop()
        except:
            pass


def main():
    """Standalone test for the hotkey manager."""
    manager = HotkeyManager()
    print("Starting hotkey manager...")
    print("Press Win+Shift+W to open command palette")
    print("Press Ctrl+C to exit")
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        manager.stop()


if __name__ == "__main__":
    main()

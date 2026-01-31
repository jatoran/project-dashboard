"""
Global Hotkey Manager for Command Palette.
Listens for configurable global hotkey and displays the command palette overlay.
"""
import threading
from pynput import keyboard
import time

from .services.config import get_config


def parse_global_hotkey(hotkey_str: str) -> dict:
    """
    Parse a hotkey string like 'win+shift+w' into components.

    Returns dict with:
        - modifiers: set of modifier key names ('win', 'shift', 'ctrl', 'alt')
        - key: the main key character (lowercase)
    """
    parts = hotkey_str.lower().split("+")
    key = parts[-1]
    modifiers = set(parts[:-1])
    return {"modifiers": modifiers, "key": key}


class HotkeyManager:
    """Manages global hotkeys and command palette window."""

    def __init__(self, palette_ui=None):
        self.listener = None
        self.current_keys = set()
        self._last_launch = 0
        self._launch_cooldown = 0.3  # Prevent rapid re-launches
        self.palette_ui = palette_ui  # Reference to the UI

        # Load hotkey from config
        config = get_config()
        self._hotkey_config = parse_global_hotkey(config.config.global_hotkey)

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

    def _check_modifiers(self) -> bool:
        """Check if all required modifier keys are pressed."""
        required = self._hotkey_config["modifiers"]

        has_win = (
            keyboard.Key.cmd in self.current_keys or
            keyboard.Key.cmd_r in self.current_keys
        )
        has_shift = (
            keyboard.Key.shift in self.current_keys or
            keyboard.Key.shift_r in self.current_keys
        )
        has_ctrl = (
            keyboard.Key.ctrl in self.current_keys or
            keyboard.Key.ctrl_r in self.current_keys
        )
        has_alt = (
            keyboard.Key.alt in self.current_keys or
            keyboard.Key.alt_r in self.current_keys or
            keyboard.Key.alt_gr in self.current_keys
        )

        # Check each required modifier
        if "win" in required and not has_win:
            return False
        if "shift" in required and not has_shift:
            return False
        if "ctrl" in required and not has_ctrl:
            return False
        if "alt" in required and not has_alt:
            return False

        return True

    def _on_press(self, key):
        """Handle key press events."""
        try:
            # Track pressed keys
            self.current_keys.add(key)

            # Check modifiers
            if not self._check_modifiers():
                return

            # Check for the target key
            target_key = self._hotkey_config["key"]
            has_key = False

            if isinstance(key, str):
                has_key = key.lower() == target_key
            elif hasattr(key, 'char') and key.char:
                has_key = key.char.lower() == target_key

            if has_key:
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

    def _format_hotkey_display(self) -> str:
        """Format hotkey for display."""
        config = get_config()
        return "+".join(part.capitalize() for part in config.config.global_hotkey.split("+"))

    def start(self):
        """Start the hotkey listener."""
        hotkey_display = self._format_hotkey_display()
        print(f"✓ Global hotkey registered: {hotkey_display}")
        print(f"  Press {hotkey_display} from anywhere to open command palette")

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
    hotkey_display = manager._format_hotkey_display()
    print("Starting hotkey manager...")
    print(f"Press {hotkey_display} to open command palette")
    print("Press Ctrl+C to exit")
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        manager.stop()


if __name__ == "__main__":
    main()

"""
Quick test script for the global hotkey feature.
Run this to test the command palette without starting the full tray app.
"""
from hotkey_manager import HotkeyManager


def main():
    print("=" * 60)
    print("COMMAND PALETTE HOTKEY TEST")
    print("=" * 60)
    print()
    print("Starting hotkey listener...")
    print()
    print("✓ Press Win+Shift+W to open command palette")
    print("✓ Press Ctrl+C to exit")
    print()
    print("Note: The API server should be running on localhost:37453")
    print("      Start it with: uv run uvicorn backend.main:app --port 37453")
    print()
    print("-" * 60)

    manager = HotkeyManager()
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\n\nStopping hotkey listener...")
        manager.stop()
        print("✓ Stopped")


if __name__ == "__main__":
    main()

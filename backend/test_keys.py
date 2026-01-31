"""
Debug script to see what keys pynput is detecting.
Run this and press Win+Shift+W to see what gets captured.
"""
from pynput import keyboard

print("Key Detection Test")
print("=" * 60)
print("Press Win+Shift+W and watch what gets detected...")
print("Press Ctrl+C to exit")
print("=" * 60)
print()

current_keys = set()

def on_press(key):
    current_keys.add(key)
    print(f"PRESSED: {key}")
    print(f"  Current keys held: {current_keys}")
    print()

def on_release(key):
    if key in current_keys:
        current_keys.remove(key)
    print(f"RELEASED: {key}")
    print(f"  Current keys held: {current_keys}")
    print()

    # Exit on Ctrl+C
    if key == keyboard.Key.esc:
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

# Global Hotkey Command Palette

Your project dashboard now has a **global hotkey command palette** that you can trigger from anywhere in Windows!

## 🚀 Features

- **Global Hotkey**: Press `Win+Shift+W` from **anywhere** to open the command palette
- **Fuzzy Search**: Type to filter projects instantly
- **Keyboard Navigation**: Arrow keys to navigate, Enter to launch
- **Multiple Actions**:
  - `Enter` → Open in VS Code
  - `Ctrl+Enter` → Open in Terminal
  - `Shift+Enter` → Open in Explorer
- **Status Indicators**: See which projects are currently running (green dot)

## 📦 Installation

Dependencies are already installed:
- `pynput` - Lightweight global hotkey listener (no keyboard lag!)
- `pywebview` - Lightweight overlay window

## 🎯 How to Use

### Option 1: Run the Tray App (Recommended)

The tray app now automatically starts the global hotkey listener:

```bash
cd backend
uv run python -m backend.tray
```

This will:
1. ✓ Start the API server on port 37453
2. ✓ Create a system tray icon
3. ✓ Register the Win+Shift+W global hotkey
4. ✓ Listen for hotkey presses in the background

### Option 2: Test Hotkey Only

To test just the hotkey feature without the tray:

```bash
# Terminal 1: Start the API server
cd backend
uv run uvicorn backend.main:app --port 37453

# Terminal 2: Start the hotkey listener
cd backend
uv run python test_hotkey.py
```

## 🎹 Keyboard Shortcuts

### In Command Palette

| Shortcut | Action |
|----------|--------|
| `Win+Shift+W` | Open command palette (from anywhere) |
| `↑` / `↓` | Navigate up/down |
| `Enter` | Open selected project in VS Code |
| `Ctrl+Enter` | Open selected project in Terminal |
| `Shift+Enter` | Open selected project in Explorer |
| `Esc` | Close command palette |

### Search Tips

The fuzzy search is smart! You can type:
- Project name: `dash` → matches "project-dashboard"
- Path parts: `proj` → matches anything in "D:\PROJECTS\..."
- Tech tags: `react` → matches projects with React

## 🔧 How It Works

1. **Hotkey Manager** (`hotkey_manager.py`)
   - Uses the `keyboard` library to register Win+Shift+W globally
   - Listens in a background thread
   - Shows a pywebview window when triggered

2. **Command Palette UI** (`command_palette.html`)
   - Lightweight HTML/CSS/JS interface
   - Fetches projects from `/api/projects`
   - Implements fuzzy search algorithm
   - Launches projects via `/api/launch` API

3. **Tray Integration** (`tray.py`)
   - Automatically starts hotkey listener on startup
   - Can also trigger palette from tray menu
   - Cleans up hotkey on exit

## 🐛 Troubleshooting

### Hotkey doesn't work
- **Admin rights**: pynput may need admin rights to capture global hotkeys
- **Conflicting software**: Another app might be using Win+Shift+W
- **Check console**: Look for "✓ Global hotkey registered" message
- **Firewall**: Make sure localhost:37453 is accessible

### Command palette shows "Failed to load projects"
- Make sure the API server is running on port 37453
- Check console for errors: Right-click → Inspect (if debug mode enabled)

### Window doesn't appear
- Check if pywebview is installed: `uv pip list | grep pywebview`
- On Windows, pywebview uses Edge WebView2 (usually pre-installed)

## 🎨 Customization

### Change the Hotkey

Edit `backend/hotkey_manager.py`:

```python
HOTKEY = "win+shift+w"  # Change this to your preferred combo
```

Examples:
- `"ctrl+shift+space"` - Ctrl+Shift+Space
- `"win+p"` - Win+P
- `"ctrl+alt+d"` - Ctrl+Alt+D

### Customize Appearance

Edit `backend/command_palette.html` to change colors, sizing, or behavior.

## 🎯 Next Steps

Future improvements you could add:
- Recent projects quick access (Ctrl+1-5)
- Multi-action launches (Code + Terminal + Explorer at once)
- Project templates/favorites
- Git operations from palette
- Docker/npm script execution

## 📝 Notes

- The hotkey listener runs as long as the tray app is running
- The command palette window is frameless and always-on-top for quick access
- Each time you open the palette, it fetches fresh project data
- The window auto-closes after launching a project

Enjoy your blazing-fast project launcher! 🔥

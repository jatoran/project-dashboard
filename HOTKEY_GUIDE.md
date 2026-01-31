# Global Hotkey Command Palette

Your project dashboard includes a **global hotkey command palette** that you can trigger from anywhere in Windows.

## Features

- **Global Hotkey**: Press `Win+Shift+W` from anywhere to open the command palette
- **Fuzzy Search**: Type to filter projects by name, path, or tech tags
- **Recency Sorting**: Most recently opened projects appear first
- **Keyboard Navigation**: Full keyboard control, no mouse needed
- **Instant Launch**: Projects open in ~15ms
- **Auto-hide**: Closes when clicking outside or pressing Escape
- **Status Indicators**: Green dot shows which projects are currently running

## Quick Start

1. Double-click `StartDashboard.vbs` to start the dashboard
2. Press `Win+Shift+W` from anywhere
3. Type to search, arrow keys to navigate, Enter to launch

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Win+Shift+W` | Open command palette (from anywhere) |
| `↑` / `↓` | Navigate up/down |
| `Enter` | Open in VS Code |
| `Ctrl+Enter` | Open in Terminal |
| `Shift+Enter` | Open in Explorer |
| `Esc` | Close command palette |

## Search Tips

The fuzzy search matches:
- **Project name**: `dash` matches "project-dashboard"
- **Path parts**: `proj` matches anything in "D:\PROJECTS\..."
- **Tech tags**: `react` matches projects with React

## How It Works

### Architecture

```
Win+Shift+W pressed
       │
       ▼
┌─────────────────────────┐
│  Hotkey Manager         │  (pynput listener in background thread)
│  hotkey_manager.py      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Command Palette UI     │  (CustomTkinter, pre-spawned, just show/hide)
│  command_palette_ui.py  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Launcher Service       │  (direct subprocess calls, cached paths)
│  launcher.py            │
└─────────────────────────┘
```

### Key Components

1. **Hotkey Manager** (`hotkey_manager.py`)
   - Uses `pynput` for global hotkey detection
   - Lightweight, no keyboard lag
   - Uses Windows API for reliable focus

2. **Command Palette UI** (`command_palette_ui.py`)
   - CustomTkinter-based frameless window
   - Runs in dedicated thread
   - Pre-spawned on startup for instant show/hide

3. **Tray Integration** (`tray.py`)
   - Initializes command palette on startup
   - Starts hotkey listener automatically
   - Command palette also available from tray menu

## Performance

| Metric | Time |
|--------|------|
| Hotkey to window visible | <50ms |
| Fuzzy search filtering | <10ms |
| Project launch | ~15ms |
| Window hide | <1ms |
| Memory footprint | ~25MB |

## Troubleshooting

### Hotkey doesn't work
- **Check console**: Run `run_tray_debug.bat` and look for "Global hotkey registered" message
- **Admin rights**: Some applications may require admin rights to capture global hotkeys
- **Conflicting software**: Another app might be using Win+Shift+W

### First launch focus issue
- The command palette uses Windows API tricks for reliable focus
- If focus fails, click the window once, then it will work

### Window doesn't appear
- Make sure the tray app is running (green icon in system tray)
- Check debug console for errors

## Dependencies

The command palette uses:
- `pynput` - Lightweight global hotkey listener
- `customtkinter` - Modern Tk-based UI framework
- `requests` - HTTP client for loading projects

These are automatically installed with the backend.

## Customization

### Change the Hotkey

Edit `backend/hotkey_manager.py` and modify the key detection in `_on_press()`:

```python
# Currently checks for Win+Shift+W
has_win = keyboard.Key.cmd in self.current_keys
has_shift = keyboard.Key.shift in self.current_keys
has_w = key.lower() == 'w' if isinstance(key, str) else False
```

### Customize Appearance

Edit `backend/command_palette_ui.py` to change colors, sizing, or behavior. The UI uses CustomTkinter widgets with a dark color scheme.

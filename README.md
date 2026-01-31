# Project Dashboard

A desktop dashboard for managing local development projects. Quickly launch projects in VS Code, terminal, or AI coding assistants (Claude Code, Codex, OpenCode) with a global hotkey command palette.

![Windows Only](https://img.shields.io/badge/platform-Windows-blue)

## Features

- **Command Palette** - Press `Win+Shift+W` from anywhere to instantly search and open projects
- **Project Cards** - Visual dashboard showing all your projects with quick-launch buttons
- **Multiple Launchers** - Open in VS Code, Terminal, File Explorer, or AI coding tools
- **Configurable** - Customize hotkeys, launchers, and file manager via JSON config
- **System Tray** - Runs quietly in the background with auto-start server

## Requirements

- **Windows 10/11** (not compatible with Linux/macOS)
- **Python 3.11+**
- **Node.js 18+**
- **uv** (Python package manager)

## Installation

### 1. Install Prerequisites

**Python 3.11+**
Download from [python.org](https://www.python.org/downloads/) or install via winget:
```powershell
winget install Python.Python.3.11
```

**Node.js 18+**
Download from [nodejs.org](https://nodejs.org/) or install via winget:
```powershell
winget install OpenJS.NodeJS.LTS
```

**uv (Python package manager)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone the Repository

```powershell
git clone https://github.com/YOUR_USERNAME/project-dashboard.git
cd project-dashboard
```

### 3. Install Dependencies

**Backend (Python)**
```powershell
cd backend
uv sync
cd ..
```

**Frontend (Node.js)**
```powershell
cd frontend
npm install
npm run build
cd ..
```

### 4. Copy Frontend Build to Backend

```powershell
Copy-Item -Recurse -Force frontend/out/* backend/frontend_dist/
```

### 5. Run the Dashboard

```powershell
uv run --project backend python -m backend.tray
```

The dashboard will:
- Start the API server on `http://localhost:37453`
- Show a system tray icon (green = running)
- Register the global hotkey `Win+Shift+W`

## Usage

### Command Palette (Win+Shift+W)

Press `Win+Shift+W` from anywhere to open the command palette:

| Key | Action |
|-----|--------|
| `Enter` | Open in VS Code |
| `Ctrl+Enter` | Open Terminal |
| `Shift+Enter` | Open File Explorer |
| `Ctrl+C` | Open Claude Code |
| `Ctrl+X` | Open Codex |
| `Ctrl+Z` | Open OpenCode |
| `Esc` | Close palette |

### Web Dashboard

Double-click the tray icon or visit `http://localhost:37453` to open the full dashboard.

### Adding Projects

1. Click "Add Project" in the dashboard
2. Enter the full path to your project folder
3. The project will be scanned and added to the dashboard

## Configuration

Settings are stored in `backend/data/config.json`:

```json
{
  "server": {
    "port": 37453
  },
  "global_hotkey": "win+shift+w",
  "file_manager": null,
  "launchers": [
    {
      "id": "vscode",
      "name": "Code",
      "command": "__vscode__",
      "hotkey": "enter",
      "enabled": true,
      "builtin": true
    },
    ...
  ]
}
```

### Configuration Options

| Option | Description |
|--------|-------------|
| `server.port` | API server port (default: 37453) |
| `global_hotkey` | Hotkey to open command palette (e.g., `win+shift+w`, `ctrl+alt+p`) |
| `file_manager` | Path to custom file manager exe, or `null` for Windows Explorer |
| `launchers` | Array of launcher button configurations |

### Adding Custom Launchers

Add a new entry to the `launchers` array:

```json
{
  "id": "npm-dev",
  "name": "Dev Server",
  "command": "npm run dev",
  "hotkey": "ctrl+d",
  "enabled": true,
  "builtin": false
}
```

Restart the tray app for changes to take effect.

## Auto-Start on Login

To start the dashboard automatically when Windows starts:

1. Press `Win+R`, type `shell:startup`, press Enter
2. Create a shortcut to `StartDashboard.vbs` in this folder

Or create a VBS file with:
```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\path\to\project-dashboard"
WshShell.Run "uv run --project backend python -m backend.tray", 0, False
```

## Project Structure

```
project-dashboard/
├── backend/
│   ├── data/              # User data (projects, config)
│   ├── frontend_dist/     # Built frontend files
│   ├── routers/           # API routes
│   ├── services/          # Business logic
│   ├── main.py            # FastAPI app
│   ├── tray.py            # System tray controller
│   ├── hotkey_manager.py  # Global hotkey listener
│   └── command_palette_ui.py  # Tkinter command palette
├── frontend/
│   └── src/               # Next.js frontend source
├── docs/                  # Documentation
└── README.md
```

## Troubleshooting

### "Win+Shift+W doesn't work"

- Make sure the tray app is running (green icon in system tray)
- Some apps may capture this hotkey first - try closing conflicting apps
- Change the hotkey in `config.json` if there's a conflict

### "Projects not showing"

- Check that project paths are valid Windows paths
- View `backend/data/projects.json` to see stored projects

### "VS Code won't open"

- Ensure VS Code is installed and `code` is in your PATH
- Run `code --version` in terminal to verify

## License

MIT

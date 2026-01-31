# Technical Documentation

## Deployment & Startup

### System Tray Application (Recommended)
The application runs as a native Windows system tray application with an integrated global hotkey command palette.

**Quick Start:**
1. Double-click `StartDashboard.vbs` (runs hidden in system tray)
2. Press `Win+Shift+W` to open the command palette from anywhere
3. Right-click the tray icon for options
4. Access full dashboard at http://localhost:37453

**Debug Mode:**
```powershell
.\run_tray_debug.bat   # Shows console output for troubleshooting
```

### Manual Development Mode
**Backend (Port 37453)**
```powershell
cd project-dashboard
uv run --project backend uvicorn backend.main:app --port 37453 --reload
```

**Frontend Development (Port 37452)**
```powershell
cd frontend
npm run dev
```

**Build Static Frontend:**
```powershell
cd frontend
npm run build
# Copy output to backend
Copy-Item -Recurse -Force out ..\backend\frontend_dist
```

## Architecture

```
project-dashboard/
├── backend/
│   ├── main.py                    # FastAPI app + static file serving
│   ├── tray.py                    # System tray controller (pystray)
│   ├── hotkey_manager.py          # Global Win+Shift+W hotkey listener
│   ├── command_palette_ui.py      # CustomTkinter command palette UI
│   ├── models.py                  # Pydantic models
│   ├── routers/
│   │   ├── projects.py            # Project CRUD, file reading, launching
│   │   ├── monitor.py             # URL status checking
│   │   └── platforms.py           # Custom links CRUD
│   ├── services/
│   │   ├── store.py               # Project data persistence + recency tracking
│   │   ├── scanner.py             # Project type detection
│   │   └── launcher.py            # VS Code/terminal launching (cached)
│   └── frontend_dist/             # Built static frontend
├── frontend/
│   └── src/app/                   # Next.js pages
├── StartDashboard.vbs             # Windowless launcher
└── install.ps1                    # Setup script
```

### Key Components

**System Tray Controller (`tray.py`)**
- Uses `pystray` for Windows system tray integration
- Manages uvicorn server lifecycle (start/stop)
- Initializes the command palette UI (pre-spawned for instant show)
- Starts the global hotkey listener
- Green icon = server running, Gray icon = stopped

**Command Palette (`command_palette_ui.py`)**
- CustomTkinter-based frameless overlay window
- Runs in dedicated thread with its own event loop
- Pre-spawned on startup for instant show/hide (<50ms)
- Fuzzy search with smart scoring
- Projects sorted by recency (most recently opened first)
- Direct launcher calls (no HTTP overhead)

**Hotkey Manager (`hotkey_manager.py`)**
- Uses `pynput` for global hotkey detection (lightweight, no keyboard lag)
- Listens for Win+Shift+W from anywhere in Windows
- Uses Windows API (`AttachThreadInput`) for reliable focus

**Launcher Service (`launcher.py`)**
- Launches VS Code, Windows Terminal, Explorer directly via `subprocess`
- Caches VS Code path (only looked up once)
- Caches Windows Terminal availability check
- No shell spawning for maximum speed (~10ms per launch)

**Static Frontend Serving**
- Frontend is built to static HTML/JS/CSS via `next build`
- FastAPI serves static files from `frontend_dist/`
- No separate frontend server needed in production

## Command Palette

### Features
- **Global Hotkey:** Press `Win+Shift+W` from anywhere to open
- **Fuzzy Search:** Matches project name, path, and tech tags
- **Recency Sorting:** Most recently opened projects appear first
- **Keyboard Navigation:** Full keyboard control, no mouse needed
- **Instant Launch:** Direct subprocess calls (~15ms total)
- **Auto-hide:** Closes when clicking outside or pressing Escape

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Win+Shift+W` | Open command palette (from anywhere) |
| `↑` / `↓` | Navigate up/down |
| `Enter` | Open in VS Code |
| `Ctrl+Enter` | Open in Terminal |
| `Shift+Enter` | Open in Explorer |
| `Esc` | Close command palette |

### Performance

| Metric | Time |
|--------|------|
| Hotkey → Window visible | <50ms |
| Fuzzy search filtering | <10ms |
| Project launch | ~15ms |
| Window hide | <1ms |
| Memory footprint | ~25MB |

## Path Handling

### Case Sensitivity Resolution
Windows filesystems are case-insensitive but case-preserving. To prevent errors when users input paths with incorrect casing (e.g., `D:\PROJECTS` vs `D:\projects`), the backend implements path resolution:
- Walks the directory tree to find exact on-disk casing
- Ensures consistent path storage regardless of input casing

## Scanner Heuristics
The `ProjectScanner` uses a waterfall approach to detect project type without running code.

### Tech Stack Detection
1. **Node.js/JS Frameworks:** Checks `package.json` for React, Vue, Next.js, NestJS, etc.
2. **Python:** Checks `requirements.txt`, `pyproject.toml` for FastAPI, Django, Flask, etc.
3. **Rust:** Checks `Cargo.toml` for Actix, Tokio, Axum
4. **Static Web:** Checks for `index.html` and `.css`/`.js` assets
5. **Other Languages:**
    - **Java:** `pom.xml`, `build.gradle`
    - **Go:** `go.mod`, `*.go`
    - **Ruby:** `Gemfile`, `*.rb`
    - **PHP:** `*.php`
6. **Docker:** Checks `docker-compose.yml` or `Dockerfile`

### Port Detection Priority
1. **Docker Compose:** `services.*.ports`
2. **Contextual Markdown:** Regex matches for `(Backend|API).*localhost:(\d+)`
3. **Frontend Config:** `.env` or `constants.ts` matches for `API_URL`
4. **Default:** `8000` (only if FastAPI detected)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/projects` | GET | List all projects (supports `sort_by_palette=true`) |
| `/api/projects` | POST | Add a project |
| `/api/projects/{id}` | DELETE | Remove a project |
| `/api/projects/{id}/refresh` | POST | Rescan project |
| `/api/projects/palette-opened` | POST | Mark project as recently opened |
| `/api/launch` | POST | Launch VS Code/terminal |
| `/api/files/content` | GET | Read file content |
| `/api/platforms` | GET/POST/DELETE | Manage custom links |
| `/api/monitor/status` | GET | Check if URL is reachable |

## Dependencies

### Backend (Python)
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pystray` - System tray integration
- `Pillow` - Icon generation
- `pynput` - Global hotkey listener
- `customtkinter` - Modern Tk-based UI
- `requests` - HTTP client

### Frontend (Node.js)
- `next` - React framework
- `react` - UI library
- `tailwindcss` - Styling
- `lucide-react` - Icons
- `@dnd-kit` - Drag and drop

## Startup Options

### Add to Windows Startup
```powershell
.\install.ps1 -WithStartup
```
This creates a shortcut in the Windows Startup folder.

### Manual Shortcut
1. Right-click `StartDashboard.vbs`
2. Select "Create shortcut"
3. Move shortcut to Startup folder (`shell:startup`)

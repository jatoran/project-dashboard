# Technical Documentation

## Deployment & Startup

### System Tray Application (Recommended)
The application runs as a native Windows system tray application.

**Quick Start:**
1. Double-click `StartDashboard.vbs` (runs hidden in system tray)
2. Right-click the tray icon for options
3. Access dashboard at http://localhost:37453

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
│   ├── main.py            # FastAPI app + static file serving
│   ├── tray.py            # System tray controller (pystray)
│   ├── routers/
│   │   ├── projects.py    # Project CRUD, file reading
│   │   ├── monitor.py     # URL status checking
│   │   └── platforms.py   # Custom links CRUD
│   ├── services/
│   │   ├── store.py       # Project data persistence
│   │   ├── scanner.py     # Project type detection
│   │   └── launcher.py    # VS Code/terminal launching
│   └── frontend_dist/     # Built static frontend
├── frontend/
│   └── src/app/           # Next.js pages
├── StartDashboard.vbs     # Windowless launcher
└── install.ps1            # Setup script
```

### Key Components

**System Tray Controller (`tray.py`)**
- Uses `pystray` for Windows system tray integration
- Manages uvicorn server lifecycle (start/stop)
- Provides menu for dashboard access and server control
- Green icon = server running, Gray icon = stopped

**Static Frontend Serving**
- Frontend is built to static HTML/JS/CSS via `next build`
- FastAPI serves static files from `frontend_dist/`
- No separate frontend server needed in production

**Direct Launching (`launcher.py`)**
- Launches VS Code, Windows Terminal, Explorer directly via `subprocess`
- No external agent or Docker needed
- Uses Windows-native commands

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
| `/api/projects` | GET | List all projects |
| `/api/projects` | POST | Add a project |
| `/api/projects/{id}` | DELETE | Remove a project |
| `/api/projects/{id}/refresh` | POST | Rescan project |
| `/api/launch` | POST | Launch VS Code/terminal |
| `/api/files/content` | GET | Read file content |
| `/api/platforms` | GET/POST/DELETE | Manage custom links |
| `/api/monitor/status` | GET | Check if URL is reachable |

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
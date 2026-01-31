# Changelog

## [2.0.0] - 2026-01-31
### Breaking Changes
- **Docker Removed:** Application no longer runs in Docker. Now runs as a native Windows system tray application.
- **Host Monitoring Removed:** Removed PC Monitoring and PC Services tabs (CPU, RAM, Network, Drives, Services, Logs).
- **WSL Button Removed:** WSL terminal launch button removed from project cards.

### Features
- **System Tray Application:** New `pystray`-based tray controller with start/stop server, open dashboard, and exit options.
- **Static Frontend:** Frontend is now built as static files and served directly by FastAPI.
- **Direct Launching:** VS Code, terminals, and Explorer now launch directly via subprocess (no host agent needed).
- **Windowless Startup:** `StartDashboard.vbs` runs the dashboard completely hidden in the system tray.

### Removed
- `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`
- `backend/routers/hoststatus.py` - Host status monitoring
- `backend/services/history.py` - DuckDB history storage
- `backend/services/cache.py` - Host metrics caching
- `frontend/src/components/MetricChart.tsx` - Charts component
- WSL/Docker path translation utilities

## [1.3.5] - 2025-11-29
### Bug Fixes
- **Copy Button Usability:**
    - Increased touch target size and added clearer hover states.
    - Added `pointer-events-none` to internal icons to prevent click capture issues.
    - Re-implemented `preventDefault` to ensure reliable event handling in complex layouts.

## [1.3.4] - 2025-11-29
### UX Improvements
- **Copy Features:**
    - **Project Path:** Clicking the project path now silently copies it to the clipboard (removed "Copied!" text overlay).
    - **Documentation:** Fixed the copy button next to markdown files which was previously unresponsive; added explicit event handling to prevent bubbling conflicts.

## [1.3.3] - 2025-11-29
### Features
- **Nested Project Scanning:**
    - Added deep scanning support for monorepo-style structures.
    - Recursively checks `frontend/`, `client/`, `web/`, `ui/`, `app/` subdirectories for `package.json` to detect tags (React, Next.js, etc.) and frontend ports if they are missing from the root.

## [1.3.2] - 2025-11-29
### Features
- **UI Layout Standardization:**
    - Migrated project card actions to a fixed 5-column grid.
    - **Consistent Buttons:** "Code", "Terminal", "WSL", and "Explorer" are now always visible and aligned.
    - **Conditional App Button:** The "App" launch button now occupies the 5th column only when a frontend URL is detected, preventing layout shifts.

## [1.3.1] - 2025-11-29
### Features
- **Enhanced Frontend Detection:**
    - **Vite Config:** Scans `vite.config.ts/js` for explicit `server.port` settings.
    - **Markdown Context:** Smarter scanning of `.md` files for URLs specifically associated with "Frontend", "UI", or "Client" labels.
    - **Docker Compose:** Improved service name matching (frontend, client, web, ui, app) and extended port validation logic (supports high ports >1024, ignores common DB ports).

## [1.3.0] - 2025-11-29
### Features
- **Frontend Monitoring:**
    - **Auto-Detection:** Scans `package.json` scripts and `docker-compose.yml` for frontend ports (3000, 4200, 5173, etc.).
    - **Live Status:** Polls the detected frontend URL every 30 seconds to check if the app is running (via HTTP HEAD request).
    - **Launch Button:** Dedicated "App" button in the project card that links to the frontend, with a color-coded status dot (Green=Up, Red=Down).

## [1.2.1] - 2025-11-29
### Features
- **Documentation Hub:**
    - The copy button next to Markdown files in the project card now copies the *content* of the file to the clipboard, consistent with the viewer modal.

## [1.2.0] - 2025-11-29
### Features
- **Enhanced Tagging:**
    - Replaced single "Project Type" with a multi-tag system.
    - Detects specific frameworks: React, Next.js, Vue, Express, NestJS, Tailwind.
    - Detects Python libs: FastAPI, Django, Flask, Pandas, PyTorch.
    - Detects Rust crates: Actix, Tokio, Axum.
    - Surfaces "Docker" as a tag alongside languages.
    - UI displays up to 3 primary tags with color-coding.

## [1.1.0] - 2025-11-29
### Features
- **Documentation Hub:**
    - Recursively scans for `.md` files in root and `docs/` folders.
    - **In-App Viewer:** Opens Markdown files in a modal with syntax highlighting (via `react-markdown`).
    - **Quick Actions:** Copy file path button next to each document.

## [1.0.0] - 2025-11-29
### Features
- **Project Dashboard:** Centralized UI to manage local projects.
- **Smart Scanning:**
    - Auto-detects Node, Python, Rust, Docker.
    - Detects FastAPI and auto-generates Swagger/ReDoc links.
    - Heuristic Port Detection (Docker Compose, README, Frontend Configs).
    - VS Code Workspace file detection (`.code-workspace`).
- **Launchers:**
    - Open in **VS Code** (opens workspace if available).
    - Open in **Explorer**.
    - Open in **Windows Terminal (WSL)** (auto-navigates to path).
- **Project Management:** Add (by path) and Remove (Trash icon).

### Infrastructure
- **Split Architecture:** Next.js Frontend (37452) + FastAPI Backend (37453).
- **Windows Native:** Optimized for running on Windows while managing WSL files.
- **VS Code Automation:** `.vscode/tasks.json` for one-click startup.

### Fixes
- **Hybrid Pathing:** solved issues with `wslpath` not working on Windows by implementing manual path conversion.
- **WSL Navigation:** solved `wt.exe` profile overrides by using `bash -c ... exec bash` pattern.
- **Port Conflicts:** Moved off default 3000/8000 ports to avoid clashes with user projects.
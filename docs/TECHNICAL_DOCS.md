# Technical Documentation

## Deployment & Startup

### Docker Compose (Recommended)
The application is designed to run as a containerized stack.

```bash
docker compose up -d --build
```
- **Frontend**: http://localhost:37452
- **Backend**: http://localhost:37453
- **Volume Mounts**:
  - `../` (Host Projects Root) -> `/mnt/d/projects` (Container) - *Changed to relative path for better WSL2 compatibility*
  - `./backend/backend/data` -> `/app/backend/data` (Persists project metadata)

### Legacy Local Development
**1. Backend (Port 37453)**
```powershell
cd backend
uv venv
.venv\Scripts\activate
fastapi dev main.py --port 37453
```

**2. Frontend (Port 37452)**
```powershell
cd frontend
npm run dev
```

## Host Status Agent Integration (The "Command Bridge")
Since the dashboard runs in a Docker container, it cannot directly launch applications or read files on the Windows host. We solve this by delegating these tasks to the **Host Status Agent**, a lightweight HTTP service running directly on the host machine.

### 1. Architecture
- **Agent URL**: `http://host.docker.internal:9876` (Configured via `HOST_AGENT_URL`).
- **Agent Mode**: The agent must run as a **User Process** (via `start_agent.bat` or startup task), not a Windows Service, to support visible GUI launching.

### 2. Capabilities
The dashboard backend proxies requests to the agent for:
*   **Application Launching** (`POST /api/launch` -> Agent `/launch`):
    *   Launches **VS Code**, **Windows Terminal**, **Explorer**, and **WSL** sessions directly on the host desktop.
*   **File Content** (`GET /api/files/content` -> Agent `/files/content`):
    *   Reads documentation files (e.g., `README.md`) from the host filesystem and serves them to the dashboard DocViewer.
*   **Service Monitoring** (`GET /api/host-status` -> Agent `/status`):
    *   Returns the status of critical host services (Docker, Tailscale, etc.).

## Path Handling & Cross-Platform Logic
The application bridges the gap between the Linux-based container environment and the Windows host filesystem.

### Path Translation
*   **Input (Adding Projects):** Windows paths (e.g., `D:\Projects\MyApp`) are automatically intercepted and converted to their WSL/Linux equivalent (e.g., `/mnt/d/Projects/MyApp`) before storage or scanning.
*   **Output (Launching/Reading):** Stored Linux paths are converted back to Windows paths before being sent to the Host Agent.

### Case Sensitivity Resolution
Linux filesystems are case-sensitive, while Windows is not. To prevent errors when users input paths with incorrect casing (e.g., `D:\PROJECTS` vs `D:\projects`), the backend implements a **path resolution mechanism**:
*   It walks the directory tree to find the exact on-disk casing for each path component.
*   This ensures that `D:\PROJECTS\myApp` correctly resolves to `/mnt/d/projects/MyApp` if that is how it exists on the disk.

## Scanner Heuristics
The `ProjectScanner` uses a waterfall approach to guess configuration without running the code.

### Tech Stack Detection
1.  **Node.js/JS Frameworks:** Checks `package.json` for React, Vue, Next.js, NestJS, Tailwind, etc.
2.  **Python:** Checks `requirements.txt`, `pyproject.toml`, etc., for FastAPI, Django, Flask, Pandas, PyTorch.
3.  **Rust:** Checks `Cargo.toml` for Actix, Tokio, Axum.
4.  **Static Web:** Checks for `index.html` in root or `public/`, and scans for `.css` and `.js` assets to identify static sites.
5.  **Other Languages:**
    *   **Java:** `pom.xml`, `build.gradle`
    *   **Go:** `go.mod`, `*.go`
    *   **Ruby:** `Gemfile`, `*.rb`
    *   **PHP:** `*.php`
6.  **Docker:** Checks `docker-compose.yml` or `Dockerfile`.

### Port Detection Priority
1.  **Docker Compose:** `services.*.ports`. Highly reliable.
2.  **Contextual Markdown:** Regex matches for `(Backend|API).*localhost:(\d+)`.
3.  **Frontend Config:** `.env` or `constants.ts` matches for `API_URL`.
4.  **Default:** `8000` (only if FastAPI is detected via `requirements.txt`).

## Known Issues / Quirks
- **Focus Stealing:** Windows blocks background apps from forcing windows to the foreground. Launched apps (Explorer, Terminal) may open in the background or flash in the taskbar.
- **Docker Path Translation:** The backend handles path translation internally (via `path_utils.py`), minimizing the need for the Host Agent to guess.
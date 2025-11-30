# Technical Documentation

## Deployment & Startup
The application requires a split-terminal setup on Windows.

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

*Automated via VS Code Task: "Run Task -> Start All"*

## Homepage Integration (Proxmox/Homepage Dashboard)
The dashboard now mirrors your self-hosted Homepage (gethomepage.dev) status tiles.

### How It Works
- **Backend endpoint**: `GET /api/homepage` (see `backend/routers/homepage.py`).
- Calls your Search Gateway `/v1/extract` using the `headless_playwright` provider to render `HOMEPAGE_URL` (defaults to `http://192.168.50.193:3000`).
- Playwright options: wait for network idle, short post-load wait, ignore HTTPS errors, include rendered HTML.
- Parses each `<li class="service" data-name="...">` block to extract:
  - Service name
  - Links and icons
  - Metrics (label/value pairs from the tile) and a short snippet
- Supported services include Sonarr, Radarr, Bazarr, Prowlarr, Proxmox, PBS Backup, OMV NAS, Flaresolverr, qBittorrent, Plex, Beszel, Scrutiny. Unknown services are ignored.
- Cache/circuit breakers are bypassed for this provider so each call is live.

### Frontend Display
- The Next.js page fetches `/api/homepage` on load and every 60 seconds.
- A "Home Dashboard" section (below the projects grid) shows each service with its icon, snippet, metrics, and primary links.

### Required Env Vars
- `GATEWAY_URL` (default `http://127.0.0.1:7083`)
- `HOMEPAGE_URL` (default `http://192.168.50.193:3000`)
- `GATEWAY_CLIENT_ID` (default `test_homepage_scrape`)
- `GATEWAY_API_KEY` (if your gateway enforces API keys)

### Notes
- Playwright must be enabled in Search Gateway (`HEADLESS_ENABLE_PLAYWRIGHT=true`) with Chromium installed.
- On Windows, the gateway must use the Proactor event loop; the gateway code already enforces this. Keep uvicorn reload off for Playwright stability.
- HTML parsing is block-based per service to avoid bleeding metrics/links across services.

## Scanner Heuristics
The `ProjectScanner` uses a waterfall approach to guess configuration without running the code.

### Port Detection Priority
1.  **Docker Compose:** `services.*.ports`. Highly reliable.
2.  **Contextual Markdown:** Regex matches for `(Backend|API).*localhost:(\d+)`.
3.  **Frontend Config:** `.env` or `constants.ts` matches for `API_URL`.
4.  **Default:** `8000` (only if FastAPI is detected via `requirements.txt`).

## Launcher Internals
### WSL Navigation
Windows Terminal (`wt.exe`) profiles often override start directories. To force a project path:
1.  Convert Windows Path (`D:\Projects\App`) -> WSL Path (`/mnt/d/Projects/App`).
2.  Construct Command:
    ```bash
    wt.exe wsl.exe -e bash -c "cd '/mnt/d/Projects/App' && exec bash"
    ```
    - `-e`: Execute command.
    - `exec bash`: Replaces the temporary command process with a fresh, interactive shell so the window stays open.

## Known Issues / Quirks
- **Case Sensitivity:** `wsl.localhost` paths are case-sensitive. Manual `/mnt/d` conversion is used to avoid `0x8007010b` errors.
- **Focus Stealing:** Windows blocks background apps (Python) from bringing windows to front. Explorer opens in the background (flashing taskbar).

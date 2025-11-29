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
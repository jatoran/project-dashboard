# System Patterns

## Architecture
- **Structure:** Polyglot Monorepo.
    - `/frontend`: Next.js 15 (App Router), Tailwind, Lucide Icons.
    - `/backend`: Python 3.12+, FastAPI.
- **Communication:** REST API (`/api/projects`, `/api/launch`) proxied via Next.js `rewrites`.

## Core Services

### 1. Project Scanner (`backend/services/scanner.py`)
A sophisticated, multi-phase analysis engine:
1.  **Tagging:** Scans root and subdirectories for `package.json`, `requirements.txt`, `Dockerfile`, `Cargo.toml`.
2.  **FastAPI Detection:** Checks for `fastapi` dependency in `requirements.txt` (including subfolders).
3.  **Port Discovery:**
    - **Docker:** Parses `docker-compose.yml` for exposed ports (e.g., `8001:8001`).
    - **Markdown:** Regex scan for "Backend running at localhost:XXXX".
    - **Config:** Scans frontend `.env`/`constants.ts` for `API_URL`.
4.  **Link Generation:** dynamically builds `http://localhost:{port}/docs` links if FastAPI or API ports are found.

### 2. Launcher (`backend/services/launcher.py`)
Handles OS-specific process spawning on Windows:
- **Explorer:** `os.startfile()` (Native shell execute).
- **VS Code:** `subprocess.Popen(["code", path], shell=True)`.
- **WSL Terminal:** `wt.exe wsl.exe -e bash -c "cd '{wsl_path}' && exec bash"`.
    - *Critical:* Uses `exec bash` to keep the shell open after navigation.
    - *Path Conversion:* Manually converts `D:\...` to `/mnt/d/...`.

## Coding Standards
- **Python:** Type hints, Pydantic models, `pathlib` for file ops.
- **Frontend:** React Functional Components, Shadcn-like styling (Tailwind).
- **Error Handling:** Scanner catches and logs errors per-file/per-step to ensure partial data is returned rather than crashing.

## Environment Constraints
- **Execution:** MUST run in Windows PowerShell.
- **Dependencies:** `uv` (Windows version) for Python.
- **Filesystem:** Hybrid. Code lives in WSL context, but execution accesses it via Windows Mounts (`D:`).
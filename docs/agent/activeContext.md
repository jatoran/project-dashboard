# Active Context

## Current Focus
Stabilizing the Backend for **Windows Native** execution.

## Recent History
- Project kickoff.
- Architecture: Next.js Frontend (Proxy) + Python FastAPI Backend.
- **Critical Issue:** Hybrid WSL/Windows filesystem permissions caused `.venv` corruption.
- **Constraint Update:** User EXPLICITLY requires Windows-side execution for the Backend.

## Immediate Goals
1.  Ensure `backend` works natively on Windows PowerShell.
2.  Provide `requirements.txt` or `pyproject.toml` that works on Windows.
3.  Guide user to re-initialize environment on Windows.

## Active Decisions
- **Runtime:** Windows (PowerShell).
- **Package Manager:** `uv` (Windows version).
- **Virtual Environment:** Must be created by Windows `uv` to generate `Scripts/activate.ps1`.

## Next Steps
- Fix dependency definition if needed.
- Provide Windows-specific commands.
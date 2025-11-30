import os
import requests
from fastapi import APIRouter, HTTPException, Response

router = APIRouter()


def _build_agent_urls():
    """Returns the base Host Agent URL and derived endpoint URLs."""
    base = os.getenv("HOST_AGENT_URL", "http://127.0.0.1:9876")
    return {
        "status": os.getenv("HOST_STATUS_URL", f"{base}/status"),
        "hardware": os.getenv("HOST_HARDWARE_URL", f"{base}/hardware"),
        "logs": os.getenv("HOST_LOGS_URL", f"{base}/logs"),
    }


def _fetch_json(url: str, params: dict | None = None):
    """Helper to GET JSON from the Host Agent with consistent error handling."""
    try:
        resp = requests.get(url, params=params, timeout=10)
    except Exception as e:  # pragma: no cover - network failure path
        raise HTTPException(status_code=502, detail=f"Host Status Agent unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    try:
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON from Host Status Agent: {e}")



@router.get("/host-status")
def get_host_status():
    urls = _build_agent_urls()
    return _fetch_json(urls["status"])


@router.get("/host-hardware")
def get_host_hardware(limit: int = 500, since: str | None = None):
    urls = _build_agent_urls()
    params = {"limit": min(max(limit, 1), 5000)}
    if since:
        params["since"] = since
    return _fetch_json(urls["hardware"], params=params)


@router.get("/host-logs")
def get_host_logs(service: str, lines: int = 200):
    urls = _build_agent_urls()
    params = {"service": service, "lines": min(max(lines, 1), 500)}
    try:
        resp = requests.get(urls["logs"], params=params, timeout=10)
    except Exception as e:  # pragma: no cover - network failure path
        raise HTTPException(status_code=502, detail=f"Host Status Agent unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    media_type = resp.headers.get("content-type", "text/plain")
    return Response(content=resp.content, media_type=media_type)

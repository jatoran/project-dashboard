import os
from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException, Response

from backend.services.cache import (
    cache, CACHE_KEY_HOST_STATUS, CACHE_KEY_HOST_HARDWARE,
    TTL_HOST_STATUS, TTL_HOST_HARDWARE
)
from backend.services.history import record_snapshot, get_history, get_stats, cleanup_old_data, backfill_from_history, get_db_info

router = APIRouter()


def _build_agent_urls():
    """Returns the base Host Agent URL and derived endpoint URLs."""
    base = os.getenv("HOST_AGENT_URL", "http://127.0.0.1:9876")
    return {
        "status": os.getenv("HOST_STATUS_URL", f"{base}/status"),
        "hardware": os.getenv("HOST_HARDWARE_URL", f"{base}/hardware"),
        "logs": os.getenv("HOST_LOGS_URL", f"{base}/logs"),
    }


def _fetch_json(url: str, params: dict | None = None) -> Dict[str, Any]:
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


def _fetch_host_status() -> Dict[str, Any]:
    """Fetch host status from agent (internal helper)."""
    urls = _build_agent_urls()
    return _fetch_json(urls["status"])


def _fetch_host_hardware(limit: int = 500, since: str | None = None) -> Dict[str, Any]:
    """Fetch host hardware data from agent (internal helper)."""
    urls = _build_agent_urls()
    params = {"limit": min(max(limit, 1), 5000)}
    if since:
        params["since"] = since
    data = _fetch_json(urls["hardware"], params=params)
    
    # Record to history database (non-blocking, don't fail if it errors)
    record_snapshot(data)
    
    return data


@router.get("/host-status")
def get_host_status():
    """Get host service status. Returns cached data if fresh."""
    cached = cache.get(CACHE_KEY_HOST_STATUS)
    if cached:
        return {
            **cached["data"],
            "last_updated": cached["last_updated"],
            "cached": True,
        }
    
    # Fetch fresh data
    data = _fetch_host_status()
    timestamp = cache.set(CACHE_KEY_HOST_STATUS, data, TTL_HOST_STATUS)
    
    return {
        **data,
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


@router.post("/host-status/refresh")
def refresh_host_status():
    """Force refresh host status, bypassing cache."""
    cache.invalidate(CACHE_KEY_HOST_STATUS)
    data = _fetch_host_status()
    timestamp = cache.set(CACHE_KEY_HOST_STATUS, data, TTL_HOST_STATUS)
    
    return {
        **data,
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


@router.get("/host-hardware")
def get_host_hardware(limit: int = 500, since: str | None = None):
    """Get host hardware metrics. Returns cached data if fresh."""
    # For hardware, we use a simpler caching strategy
    # since params like limit/since may vary
    cached = cache.get(CACHE_KEY_HOST_HARDWARE)
    if cached and not since:  # Only use cache for default queries
        return {
            **cached["data"],
            "last_updated": cached["last_updated"],
            "cached": True,
        }
    
    # Fetch fresh data
    data = _fetch_host_hardware(limit, since)
    if not since:  # Only cache default queries
        timestamp = cache.set(CACHE_KEY_HOST_HARDWARE, data, TTL_HOST_HARDWARE)
        return {
            **data,
            "last_updated": timestamp.isoformat(),
            "cached": False,
        }
    
    return data


@router.post("/host-hardware/refresh")
def refresh_host_hardware():
    """Force refresh host hardware data, bypassing cache."""
    cache.invalidate(CACHE_KEY_HOST_HARDWARE)
    data = _fetch_host_hardware()
    timestamp = cache.set(CACHE_KEY_HOST_HARDWARE, data, TTL_HOST_HARDWARE)
    
    return {
        **data,
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


@router.get("/host-logs")
def get_host_logs(service: str, lines: int = 200):
    """Get host service logs. Not cached due to realtime nature."""
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


@router.get("/history")
def get_hardware_history(minutes: int = 60):
    """
    Get hardware metrics history for the specified time range.
    Default is last 60 minutes. Max is 10080 (7 days).
    """
    minutes = min(max(minutes, 1), 10080)  # 1 min to 7 days
    data = get_history(minutes)
    return {
        "history": data,
        "minutes": minutes,
        "count": len(data),
    }


@router.get("/history/stats")
def get_hardware_stats(minutes: int = 60):
    """
    Get aggregated statistics for the specified time range.
    Returns min/max/avg for each metric.
    """
    minutes = min(max(minutes, 1), 10080)
    stats = get_stats(minutes)
    return {
        "stats": stats,
        "minutes": minutes,
    }


@router.post("/history/cleanup")
def cleanup_history(days: int = 7):
    """
    Delete history data older than the specified number of days.
    Default is 7 days.
    """
    days = min(max(days, 1), 365)
    deleted = cleanup_old_data(days)
    return {
        "deleted": deleted,
        "days_kept": days,
    }


@router.get("/history/debug")
def debug_history():
    """Debug endpoint showing database state."""
    return get_db_info()


@router.post("/history/backfill")
def backfill_history(limit: int = 5000):
    """
    Backfill DuckDB history from the host-status-agent's existing data.
    Fetches in batches of up to 5000 records for reliability.
    Call multiple times to get more data (it skips duplicates automatically).
    """
    limit = min(max(limit, 100), 5000)  # Cap at 5000 per batch
    
    # Fetch history from agent
    urls = _build_agent_urls()
    try:
        resp = requests.get(urls["hardware"], params={"limit": limit}, timeout=60)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Agent unreachable: {e}")
    
    history = data.get("history", [])
    if not history:
        return {"inserted": 0, "message": "No history data from agent"}
    
    # Backfill into DuckDB
    inserted = backfill_from_history(history)
    
    # Get current DB state
    db_info = get_db_info()
    
    return {
        "inserted": inserted,
        "fetched": len(history),
        "total_records": db_info.get("total_records", 0),
        "oldest": db_info.get("oldest"),
        "newest": db_info.get("newest"),
    }

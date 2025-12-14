import os
import re
from typing import List, Dict, Any

import requests
from fastapi import APIRouter, HTTPException

from backend.services.cache import (
    cache, CACHE_KEY_SCRUTINY, TTL_SCRUTINY
)

router = APIRouter()


def _parse_drives(text: str) -> List[Dict[str, str]]:
    drives = []
    t = re.sub(r"[ \t]+", " ", text.replace("\r", ""))
    pattern = re.compile(
        r"(/dev/[^\s]+)\s+-\s+([^-]+?)\s+-\s+([^\n]+?)\s+Last Updated on\s+([^\n]+?)\s+Status\s+([^\n]+?)\s+Temperature\s+([^\n]+?)\s+Capacity\s+([^\n]+?)\s+Powered On\s+([^\n]+?)\s+(?=/dev/|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(t):
        device = m.group(1).strip()
        bus = m.group(2).strip()
        model = m.group(3).strip()
        last_updated = m.group(4).strip()
        status = m.group(5).strip()
        temp = m.group(6).strip()
        capacity = m.group(7).strip()
        powered_on = m.group(8).strip()
        drives.append(
            {
                "device": device,
                "bus_model": f"{bus} - {model}",
                "last_updated": last_updated,
                "status": status,
                "temp": temp,
                "capacity": capacity,
                "powered_on": powered_on,
            }
        )
    return drives


def _fetch_scrutiny_data() -> Dict[str, Any]:
    """Fetch scrutiny data from external gateway (internal helper)."""
    gateway_url = os.getenv("GATEWAY_URL", "http://127.0.0.1:7083")
    scrutiny_url = os.getenv("SCRUTINY_URL", "http://192.168.50.193:8081/web/dashboard")
    client_id = os.getenv("GATEWAY_CLIENT_ID", "test_homepage_scrape")
    api_key = os.getenv("GATEWAY_API_KEY")

    payload = {
        "provider": "headless_playwright",
        "urls": [scrutiny_url],
        "options": {
            "timeout_ms": 40000,
            "render": "always",
            "format": "text",
            "extract_depth": "advanced",
            "wait_until": "networkidle",
            "wait_for_timeout_ms": 8000,
            "include_html": True,
            "ignore_https_errors": True,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Client-Id": client_id,
    }
    if api_key:
        headers["X-Api-Key"] = api_key

    try:
        resp = requests.post(f"{gateway_url}/v1/extract", json=payload, headers=headers, timeout=60)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gateway request failed: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    items = data.get("items") or data.get("results") or []
    if not items:
        raise HTTPException(status_code=502, detail="Gateway returned no items")

    blobs = []
    for item in items:
        for key in ("html", "content", "text", "raw_html", "raw_content", "body"):
            val = item.get(key)
            if isinstance(val, str):
                blobs.append(val)
        meta = item.get("provider_meta") or {}
        if isinstance(meta, dict):
            raw_html = meta.get("html")
            if isinstance(raw_html, str):
                blobs.append(raw_html)

    if not blobs:
        raise HTTPException(status_code=502, detail="Gateway returned no textual/HTML content")

    aggregated = " ".join(blobs)
    drives = _parse_drives(aggregated)
    return {"drives": drives}


@router.get("/scrutiny")
def get_scrutiny_data():
    """Get scrutiny drive data. Returns cached data if fresh."""
    cached = cache.get(CACHE_KEY_SCRUTINY)
    if cached:
        return {
            "drives": cached["data"]["drives"],
            "last_updated": cached["last_updated"],
            "cached": True,
        }
    
    # Fetch fresh data
    data = _fetch_scrutiny_data()
    timestamp = cache.set(CACHE_KEY_SCRUTINY, data, TTL_SCRUTINY)
    
    return {
        "drives": data["drives"],
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


@router.post("/scrutiny/refresh")
def refresh_scrutiny_data():
    """Force refresh scrutiny data, bypassing cache."""
    cache.invalidate(CACHE_KEY_SCRUTINY)
    data = _fetch_scrutiny_data()
    timestamp = cache.set(CACHE_KEY_SCRUTINY, data, TTL_SCRUTINY)
    
    return {
        "drives": data["drives"],
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


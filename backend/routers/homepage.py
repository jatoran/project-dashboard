import os
import re
from typing import List, Dict, Any

import requests
from fastapi import APIRouter, HTTPException

from backend.services.cache import (
    cache, CACHE_KEY_HOMEPAGE, TTL_HOMEPAGE
)

router = APIRouter()

# Known services to extract from the Homepage dashboard.
SERVICE_NAMES = {
    "Sonarr",
    "Radarr",
    "Bazarr",
    "Prowlarr",
    "Proxmox",
    "PBS Backup",
    "OMV NAS",
    "Flaresolverr",
    "qBittorrent",
    "Plex",
    "Beszel",
    "Scrutiny",
}


def _find_service_block(html: str, service_name: str) -> str:
    pattern = (
        r"<li[^>]*class=\"[^\"]*service[^\"]*\"[^>]*>.*?"
        + re.escape(service_name)
        + r".*?</li>"
    )
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    return match.group(0) if match else ""


def _extract_links(block_html: str) -> List[str]:
    return re.findall(r'href=["\']([^"\']+)["\']', block_html, flags=re.IGNORECASE)


def _extract_icons(block_html: str) -> List[str]:
    return re.findall(r'src=["\']([^"\']+)["\']', block_html, flags=re.IGNORECASE)


def _extract_metrics(block_html: str) -> List[Dict[str, str]]:
    pairs = re.findall(
        r'<div class="font-thin text-sm">\s*([^<]+?)\s*</div>\s*'
        r'<div class="font-bold text-xs uppercase">\s*([^<]+?)\s*</div>',
        block_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    metrics = []
    for value, label in pairs:
        metrics.append({"label": label.strip(), "value": value.strip()})
    return metrics


def _parse_services(html: str) -> List[Dict[str, Any]]:
    services: List[Dict[str, Any]] = []
    # Match each service block explicitly so we don't mix content between services.
    matches = re.findall(
        r'<li[^>]*class="[^"]*service[^"]*"[^>]*data-name="([^"]+)"[^>]*>(.*?)</li>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for name, block in matches:
        if name not in SERVICE_NAMES:
            continue
        links = list(dict.fromkeys(_extract_links(block)))
        icons = list(dict.fromkeys(_extract_icons(block)))
        metrics = _extract_metrics(block)
        # Snippet is derived from the block only.
        text_only = re.sub(r"<[^>]+>", " ", block)
        text_only = re.sub(r"\s+", " ", text_only).strip()
        snippet = text_only[:180]
        services.append(
            {
                "name": name,
                "links": links,
                "icons": icons,
                "metrics": metrics,
                "snippet": snippet,
            }
        )
    return services


def _fetch_homepage_data() -> Dict[str, Any]:
    """Fetch homepage data from external gateway (internal helper)."""
    gateway_url = os.getenv("GATEWAY_URL", "http://127.0.0.1:7083")
    homepage_url = os.getenv("HOMEPAGE_URL", "http://192.168.50.193:3000")
    client_id = os.getenv("GATEWAY_CLIENT_ID", "test_homepage_scrape")
    api_key = os.getenv("GATEWAY_API_KEY")

    payload = {
        "provider": "headless_playwright",
        "urls": [homepage_url],
        "options": {
            "timeout_ms": 40000,
            "render": "always",
            "format": "text",
            "extract_depth": "advanced",
            "wait_until": "networkidle",
            "wait_for_text": "Sonarr",
            "wait_for_timeout_ms": 12000,
            "include_html": True,
            "ignore_https_errors": True,
            "include_console_logs": False,
            "include_network_errors": False,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Client-Id": client_id,
    }
    if api_key:
        headers["X-Api-Key"] = api_key

    try:
        resp = requests.post(
            f"{gateway_url}/v1/extract", json=payload, headers=headers, timeout=60
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gateway request failed: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    items = data.get("items") or data.get("results") or []
    if not items:
        raise HTTPException(status_code=502, detail="Gateway returned no items")

    html_parts = []
    for item in items:
        for key in ("html", "content", "text", "raw_html", "raw_content", "body"):
            val = item.get(key)
            if isinstance(val, str):
                html_parts.append(val)
        meta = item.get("provider_meta") or {}
        if isinstance(meta, dict):
            raw_html = meta.get("html")
            if isinstance(raw_html, str):
                html_parts.append(raw_html)

    if not html_parts:
        raise HTTPException(status_code=502, detail="Gateway returned no HTML/text content")

    html_blob = " ".join(html_parts)
    services = _parse_services(html_blob)
    return {"services": services}


@router.get("/homepage")
def get_homepage_data():
    """Get homepage data. Returns cached data if fresh."""
    cached = cache.get(CACHE_KEY_HOMEPAGE)
    if cached:
        return {
            "services": cached["data"]["services"],
            "last_updated": cached["last_updated"],
            "cached": True,
        }
    
    # Fetch fresh data
    data = _fetch_homepage_data()
    timestamp = cache.set(CACHE_KEY_HOMEPAGE, data, TTL_HOMEPAGE)
    
    return {
        "services": data["services"],
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


@router.post("/homepage/refresh")
def refresh_homepage_data():
    """Force refresh homepage data, bypassing cache."""
    cache.invalidate(CACHE_KEY_HOMEPAGE)
    data = _fetch_homepage_data()
    timestamp = cache.set(CACHE_KEY_HOMEPAGE, data, TTL_HOMEPAGE)
    
    return {
        "services": data["services"],
        "last_updated": timestamp.isoformat(),
        "cached": False,
    }


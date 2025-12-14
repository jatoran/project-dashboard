"""
API Platforms router - CRUD for custom saved links.
"""

import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Data file path
DATA_DIR = Path(__file__).parent.parent / "data"
PLATFORMS_FILE = DATA_DIR / "platforms.json"


class Platform(BaseModel):
    """A saved platform/link."""
    id: str
    name: str
    url: str


class CreatePlatformRequest(BaseModel):
    """Request to create a new platform."""
    name: str
    url: str


def _ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_platforms() -> List[Platform]:
    """Load platforms from JSON file."""
    _ensure_data_dir()
    if not PLATFORMS_FILE.exists():
        return []
    try:
        with open(PLATFORMS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Platform(**p) for p in data]
    except (json.JSONDecodeError, KeyError):
        return []


def _save_platforms(platforms: List[Platform]):
    """Save platforms to JSON file."""
    _ensure_data_dir()
    with open(PLATFORMS_FILE, "w", encoding="utf-8") as f:
        json.dump([p.model_dump() for p in platforms], f, indent=2)


@router.get("/platforms")
def list_platforms() -> List[Platform]:
    """List all saved platforms."""
    return _load_platforms()


@router.post("/platforms")
def create_platform(req: CreatePlatformRequest) -> Platform:
    """Create a new platform link."""
    platforms = _load_platforms()
    
    # Check for duplicate name
    if any(p.name.lower() == req.name.lower() for p in platforms):
        raise HTTPException(status_code=400, detail="Platform with this name already exists")
    
    platform = Platform(
        id=str(uuid.uuid4()),
        name=req.name,
        url=req.url,
    )
    platforms.append(platform)
    _save_platforms(platforms)
    
    return platform


@router.delete("/platforms/{platform_id}")
def delete_platform(platform_id: str) -> dict:
    """Delete a platform by ID."""
    platforms = _load_platforms()
    original_count = len(platforms)
    
    platforms = [p for p in platforms if p.id != platform_id]
    
    if len(platforms) == original_count:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    _save_platforms(platforms)
    return {"deleted": True, "id": platform_id}

"""Config API routes."""

from fastapi import APIRouter
from ..services.config import get_config

router = APIRouter()


@router.get("/config")
def get_full_config():
    """Get the full configuration."""
    config = get_config()
    return {
        "port": config.config.port,
        "global_hotkey": config.config.global_hotkey,
        "file_manager": config.config.file_manager,
        "launchers": config.config.launchers,
    }


@router.get("/config/launchers")
def get_launchers():
    """Get enabled launchers only (for UI buttons)."""
    config = get_config()
    return config.get_launchers(enabled_only=True)


@router.put("/config")
def update_config(data: dict):
    """Update configuration values."""
    config = get_config()
    config.update(**data)
    return {"status": "ok"}

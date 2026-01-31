from fastapi import APIRouter
import requests
from typing import Dict

router = APIRouter()


@router.get("/monitor/status", response_model=Dict[str, bool])
def check_status(url: str):
    """
    Checks if a URL is reachable.
    Returns {"is_up": true/false}.
    """
    try:
        # Use a short timeout. A 'head' request is lighter than 'get'.
        # We just want to know if something is listening.
        response = requests.head(url, timeout=1.5)
        # Any response code usually means *something* is listening (even 404 or 500)
        # ConnectionRefused is what we want to catch as "Down".
        return {"is_up": True}
    except requests.exceptions.ConnectionError:
        return {"is_up": False}
    except requests.exceptions.Timeout:
        return {"is_up": False}
    except Exception:
        return {"is_up": False}

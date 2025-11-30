import os
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/host-status")
def get_host_status():
    agent_url = os.getenv("HOST_STATUS_URL", "http://127.0.0.1:9876/status")
    try:
        resp = requests.get(agent_url, timeout=8)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Host Status Agent unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    try:
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON from Host Status Agent: {e}")

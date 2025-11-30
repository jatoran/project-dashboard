import subprocess
import os
import shutil
import requests
from fastapi import HTTPException
from backend.utils.path_utils import linux_to_windows

class Launcher:
    def __init__(self):
        self.host_agent_url = os.getenv("HOST_AGENT_URL", "http://host.docker.internal:9876")
        if self.host_agent_url:
            print(f"Launcher will use host agent at: {self.host_agent_url}")
        else:
            print("WARNING: HOST_AGENT_URL not set. Launch functionality will be disabled.")

    def launch(self, path: str, launch_type: str):
        if not self.host_agent_url:
            raise HTTPException(status_code=501, detail="Launch functionality disabled (HOST_AGENT_URL not set).")

        # The host agent expects Windows paths. The dashboard backend holds Linux paths (Project.path).
        # So we convert Linux -> Windows.
        win_path = linux_to_windows(path)

        payload = {"path": win_path, "type": launch_type}
        try:
            response = requests.post(f"{self.host_agent_url}/launch", json=payload, timeout=5)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            result = response.json()
            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=f"Host agent launch error: {result.get('message')}")
            print(f"Successfully sent launch request to host agent: {launch_type} {path} -> {win_path}")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Failed to connect to host agent for launch: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error during host agent launch: {e}")

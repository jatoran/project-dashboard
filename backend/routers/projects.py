import os
import requests
from fastapi import APIRouter, HTTPException
from typing import List
from backend.models import Project, CreateProjectRequest, LaunchRequest, AddLinkRequest, AddDocRequest, PortOverrideRequest, ReorderRequest
from backend.services.store import ProjectStore
from backend.services.launcher import Launcher
from backend.utils.path_utils import linux_to_windows

router = APIRouter()
store = ProjectStore()
launcher = Launcher()

@router.get("/projects", response_model=List[Project])
def get_projects():
    return store.get_all()

# ... [keep existing endpoints] ...

@router.post("/projects/{project_id}/links", response_model=Project)
def add_custom_link(project_id: str, request: AddLinkRequest):
    try:
        return store.add_custom_link(project_id, request.name, request.url)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/projects/{project_id}/links/{name}", response_model=Project)
def remove_custom_link(project_id: str, name: str):
    try:
        return store.remove_custom_link(project_id, name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/projects/{project_id}/custom-docs", response_model=Project)
def add_custom_doc(project_id: str, request: AddDocRequest):
    try:
        return store.add_custom_doc(project_id, request.name, request.path)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/projects/{project_id}/custom-docs/{name}", response_model=Project)
def remove_custom_doc(project_id: str, name: str):
    try:
        return store.remove_custom_doc(project_id, name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/projects/{project_id}/ports", response_model=Project)
def update_ports(project_id: str, request: PortOverrideRequest):
    try:
        return store.update_ports(project_id, request.frontend_port, request.backend_port)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/files/content")
def get_file_content(path: str):
    """Reads and returns the content of a file via the host agent."""
    host_agent_url = os.getenv("HOST_AGENT_URL", "http://host.docker.internal:9876")

    if not host_agent_url:
        raise HTTPException(status_code=501, detail="File content functionality disabled (HOST_AGENT_URL not set).")

    try:
        # The host agent expects Windows paths. The dashboard backend holds Linux paths.
        # So we convert.
        win_path = linux_to_windows(path)
        
        response = requests.get(f"{host_agent_url}/files/content", params={"path": win_path}, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        agent_response = response.json()
        if response.status_code == 200 and "status" in agent_response and agent_response["status"] == "error":
            raise HTTPException(status_code=404, detail=agent_response.get('message', 'File not found via agent'))
        
        return agent_response
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to host agent for file content: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during host agent file content fetch: {e}")

@router.post("/projects", response_model=Project)
def add_project(request: CreateProjectRequest):
    print(f"[DEBUG] Router received add_project request: {request}")
    try:
        return store.add_project(request.path)
    except ValueError as e:
        print(f"[ERROR] Router caught ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Router caught unexpected exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    try:
        store.remove_project(project_id)
        return {"status": "success", "message": f"Project {project_id} removed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/launch")
def launch_project(request: LaunchRequest):
    try:
        launcher.launch(request.project_path, request.launch_type)
        return {"status": "success", "message": f"Launched {request.launch_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/reorder", response_model=List[Project])
def reorder_projects(request: ReorderRequest):
    """Update project positions based on provided order of IDs."""
    try:
        return store.reorder(request.order)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/{project_id}/refresh", response_model=Project)
def refresh_project(project_id: str):
    """Rescan a project to update discovered docs and metadata."""
    try:
        return store.refresh_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

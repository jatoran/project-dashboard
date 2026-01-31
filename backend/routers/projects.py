import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List
from ..models import Project, CreateProjectRequest, LaunchRequest, AddLinkRequest, AddDocRequest, PortOverrideRequest, ReorderRequest
from ..services.store import ProjectStore
from ..services.launcher import Launcher

router = APIRouter()
store = ProjectStore()
launcher = Launcher()


@router.get("/projects", response_model=List[Project])
def get_projects(sort_by_palette: bool = False):
    """Get all projects. If sort_by_palette=True, sort by command palette recency."""
    return store.get_all(sort_by_palette_recency=sort_by_palette)


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
    """Read and return the content of a file directly from the filesystem."""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
        
        # Try to detect encoding
        content = None
        for encoding in ['utf-8', 'utf-16', 'latin-1']:
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise HTTPException(status_code=500, detail="Unable to read file (encoding issue)")
        
        return {"content": content, "path": str(file_path)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")


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


@router.post("/projects/palette-opened")
def mark_palette_opened(request: LaunchRequest):
    """Mark a project as recently opened from the command palette."""
    try:
        store.mark_palette_open(request.project_path)
        return {"status": "success"}
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

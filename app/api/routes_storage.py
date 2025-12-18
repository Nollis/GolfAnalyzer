from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from app.core.storage import get_storage, LocalStorage
from pathlib import Path
import os

router = APIRouter()

@router.get("/storage/{key:path}", tags=["storage"])
async def get_storage_file(key: str):
    """
    Serve a file from the storage abstraction.
    In production (S3), this route wouldn't be hit because get_url() would return a presigned S3 URL.
    This is for the 'Local impl'.
    """
    storage = get_storage()
    
    # Safety check for LocalStorage to prevent directory traversal
    if isinstance(storage, LocalStorage):
        path = storage.get_path(key)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(path)
    else:
        # If we are using S3 but this route is hit, redirect?
        # For now, assume this route only meant for Local.
        return HTTPException(status_code=400, detail="Storage provider does not support direct download")

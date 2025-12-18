from abc import ABC, abstractmethod
import os
import shutil
from pathlib import Path
from typing import Union, BinaryIO

class BaseStorage(ABC):
    """Abstract base class for file storage"""
    
    @abstractmethod
    def save(self, file_obj: Union[str, Path, BinaryIO], key: str) -> str:
        """
        Save a file to storage.
        Args:
            file_obj: Path to file (str/Path) or file-like object (BinaryIO)
            key: unique key (filename/path) for the file
        Returns:
            str: Publicly accessible URL or identifier
        """
        pass

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get public URL for a key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a file by key"""
        pass
        
    @abstractmethod
    def get_path(self, key: str) -> str:
        """Get local filesystem path (if applicable, for processing tools)"""
        pass

class LocalStorage(BaseStorage):
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def save(self, file_obj: Union[str, Path, BinaryIO], key: str) -> str:
        target_path = self.base_dir / key
        
        # Ensure parent dir exists (if key has subdirs)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(file_obj, (str, Path)):
            # Copy from path
            shutil.copy2(file_obj, target_path)
        else:
            # Write from file-like object
            with open(target_path, "wb") as f:
                if hasattr(file_obj, "read"):
                    shutil.copyfileobj(file_obj, f)
                else:
                    f.write(file_obj)
                    
        return self.get_url(key)
        
    def get_url(self, key: str) -> str:
        # In a real app, this would point to a static file server or generic endpoint
        # For now, we point to a generic storage retrieval endpoint we'll create
        return f"/api/v1/storage/{key}"
        
    def delete(self, key: str) -> bool:
        target_path = self.base_dir / key
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def get_path(self, key: str) -> str:
        """Helper for local processing tools (FFmpeg, OpenCV) that need a real path"""
        return str((self.base_dir / key).absolute())

# Singleton / Factory
_storage_instance = None

def get_storage() -> BaseStorage:
    global _storage_instance
    if _storage_instance is None:
        # In future: Check env var STORAGE_PROVIDER=s3
        _storage_instance = LocalStorage()
    return _storage_instance

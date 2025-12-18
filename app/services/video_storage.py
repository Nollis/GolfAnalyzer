from pathlib import Path
from typing import Optional
from app.core.storage import get_storage

class VideoStorage:
    """Service for managing video file storage using the core Storage Abstraction"""
    
    def __init__(self):
        self.storage = get_storage()
    
    def _get_key(self, session_id: str) -> str:
        return f"videos/{session_id}.mp4"

    def save_video(self, temp_file_path: str, session_id: str) -> str:
        """
        Save video file permanently to storage.
        Returns the storage KEY.
        """
        key = self._get_key(session_id)
        self.storage.save(temp_file_path, key)
        return key
    
    def get_video_path(self, session_id: str) -> Optional[Path]:
        """
        Get local path to video file (if available).
        """
        key = self._get_key(session_id)
        try:
            path_str = self.storage.get_path(key)
            return Path(path_str)
        except NotImplementedError:
            return None
    
    def get_video_url(self, session_id: str) -> str:
        """
        Get URL for video file
        """
        key = self._get_key(session_id)
        return self.storage.get_url(key)
    
    def delete_video(self, session_id: str) -> bool:
        """
        Delete video file
        """
        key = self._get_key(session_id)
        return self.storage.delete(key)


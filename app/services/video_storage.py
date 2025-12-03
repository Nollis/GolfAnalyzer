import os
import shutil
from pathlib import Path
from typing import Optional
import uuid

class VideoStorage:
    """Service for managing video file storage"""
    
    def __init__(self, storage_dir: str = "videos"):
        self.storage_dir = Path(storage_dir)
        # Create videos directory if it doesn't exist
        self.storage_dir.mkdir(exist_ok=True)
    
    def save_video(self, temp_file_path: str, session_id: str) -> str:
        """
        Save video file permanently
        
        Args:
            temp_file_path: Path to temporary uploaded file
            session_id: Session ID to use as filename
            
        Returns:
            Relative path to saved video
        """
        # Use session_id as filename to ensure uniqueness
        video_filename = f"{session_id}.mp4"
        video_path = self.storage_dir / video_filename
        
        # Copy temp file to permanent location
        shutil.copy2(temp_file_path, video_path)
        
        # Return relative path
        return str(video_path)
    
    def get_video_path(self, session_id: str) -> Optional[Path]:
        """
        Get full path to video file
        
        Args:
            session_id: Session ID
            
        Returns:
            Full path to video file, or None if not found
        """
        video_path = self.storage_dir / f"{session_id}.mp4"
        if video_path.exists():
            return video_path
        return None
    
    def get_video_url(self, session_id: str) -> str:
        """
        Get URL for video file
        
        Args:
            session_id: Session ID
            
        Returns:
            URL path to video
        """
        return f"/api/v1/sessions/{session_id}/video"
    
    def delete_video(self, session_id: str) -> bool:
        """
        Delete video file
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted, False if not found
        """
        video_path = self.storage_dir / f"{session_id}.mp4"
        if video_path.exists():
            video_path.unlink()
            return True
        return False

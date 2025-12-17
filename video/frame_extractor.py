"""
Video Frame Extractor

Utility to extract specific frames from video files using OpenCV.
"""

import cv2
from pathlib import Path
from typing import Union


def save_frame(video_path: Union[str, Path], frame_idx: int, out_path: Union[str, Path]) -> None:
    """
    Extract a specific frame from a video and save it as an image.
    
    Args:
        video_path: Path to the input video file
        frame_idx: Frame number to extract (0-indexed)
        out_path: Path to save the extracted frame (PNG or JPG)
        
    Raises:
        RuntimeError: If the video cannot be opened or the frame cannot be read
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    
    if not video_path.exists():
        raise RuntimeError(f"Video file not found: {video_path}")
    
    # Create output directory if needed
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    
    try:
        # Get total frame count for validation
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if frame_idx < 0 or frame_idx >= total_frames:
            raise RuntimeError(
                f"Frame index {frame_idx} out of range. Video has {total_frames} frames (0-{total_frames-1})."
            )
        
        # Seek to the frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        
        ret, frame = cap.read()
        
        if not ret or frame is None:
            raise RuntimeError(f"Could not read frame {frame_idx} from video: {video_path}")
        
        # Save the frame
        success = cv2.imwrite(str(out_path), frame)
        
        if not success:
            raise RuntimeError(f"Failed to write frame to: {out_path}")
            
    finally:
        cap.release()


def get_frame_count(video_path: Union[str, Path]) -> int:
    """
    Get the total number of frames in a video.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Total frame count
        
    Raises:
        RuntimeError: If the video cannot be opened
    """
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    
    try:
        return int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()


def get_video_fps(video_path: Union[str, Path]) -> float:
    """
    Get the FPS of a video.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Frames per second
        
    Raises:
        RuntimeError: If the video cannot be opened
    """
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0
    finally:
        cap.release()

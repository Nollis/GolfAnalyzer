# pose/yolo_pose_extractor.py
"""
YOLOv8-pose based pose extraction using Ultralytics.

YOLOv8-pose is a state-of-the-art pose estimation model that combines
object detection with keypoint estimation in a single pass.

Key advantages over MediaPipe:
- Better accuracy on occluded joints
- More robust to different camera angles
- Faster inference (single-stage detection)
- Better handling of motion blur
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# YOLOv8 imports (optional)
YOLO_AVAILABLE = False
_yolo_model = None

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Ultralytics (YOLOv8) not available: {e}")
    logger.warning("Install with: pip install ultralytics")

# COCO keypoint indices (17 keypoints) - same format as YOLOv8-pose output
COCO_KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]

# Mapping from COCO 17 keypoints to MediaPipe 33 landmark indices
COCO_TO_MEDIAPIPE = {
    0: 0,    # nose -> nose
    1: 2,    # left_eye -> left_eye
    2: 5,    # right_eye -> right_eye
    3: 7,    # left_ear -> left_ear
    4: 8,    # right_ear -> right_ear
    5: 11,   # left_shoulder -> left_shoulder
    6: 12,   # right_shoulder -> right_shoulder
    7: 13,   # left_elbow -> left_elbow
    8: 14,   # right_elbow -> right_elbow
    9: 15,   # left_wrist -> left_wrist
    10: 16,  # right_wrist -> right_wrist
    11: 23,  # left_hip -> left_hip
    12: 24,  # right_hip -> right_hip
    13: 25,  # left_knee -> left_knee
    14: 26,  # right_knee -> right_knee
    15: 27,  # left_ankle -> left_ankle
    16: 28,  # right_ankle -> right_ankle
}


def get_yolo_model():
    """Get or initialize the YOLOv8-pose model (singleton)."""
    global _yolo_model
    
    if not YOLO_AVAILABLE:
        return None
    
    if _yolo_model is None:
        try:
            logger.info("Initializing YOLOv8-pose model...")
            # Use yolov8x-pose for best accuracy (can also use yolov8n-pose for speed)
            _yolo_model = YOLO('yolov8x-pose.pt')
            logger.info("YOLOv8-pose model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YOLOv8-pose: {e}")
            return None
    
    return _yolo_model


PoseFrame = Dict[str, Any]


def _coco_to_mediapipe_landmarks(keypoints: np.ndarray, img_width: int, img_height: int) -> List[Dict[str, float]]:
    """
    Convert COCO 17-keypoint format to MediaPipe 33-landmark format.
    
    Args:
        keypoints: (17, 3) array - x, y, confidence for each keypoint
        img_width: Image width for normalization
        img_height: Image height for normalization
    
    Returns:
        List of 33 landmarks in MediaPipe format (normalized coordinates)
    """
    # Initialize 33 landmarks with zeros
    landmarks = []
    for i in range(33):
        landmarks.append({
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "visibility": 0.0,
        })
    
    # Map COCO keypoints to MediaPipe positions
    for coco_idx, mp_idx in COCO_TO_MEDIAPIPE.items():
        if coco_idx < len(keypoints):
            x_px, y_px, conf = keypoints[coco_idx]
            
            landmarks[mp_idx] = {
                "x": float(x_px / img_width),
                "y": float(y_px / img_height),
                "z": 0.0,  # YOLOv8-pose is 2D
                "visibility": float(conf),
            }
    
    # Interpolate missing MediaPipe landmarks from available ones
    # Mouth corners (9, 10) - approximate from nose
    if landmarks[0]["visibility"] > 0:
        landmarks[9] = landmarks[0].copy()
        landmarks[9]["y"] += 0.02
        landmarks[10] = landmarks[0].copy()
        landmarks[10]["y"] += 0.02
    
    # Eye inner/outer (1, 3, 4, 6) - approximate from eyes
    for eye_idx, inner_idx, outer_idx in [(2, 1, 3), (5, 4, 6)]:
        if landmarks[eye_idx]["visibility"] > 0:
            landmarks[inner_idx] = landmarks[eye_idx].copy()
            landmarks[outer_idx] = landmarks[eye_idx].copy()
    
    return landmarks


def extract_pose_frames_yolo(video_path: Path, max_frames: int | None = None, frame_step: int = 1) -> List[PoseFrame]:
    """
    Extract pose landmarks using YOLOv8-pose.
    
    Returns frames in the same format as MediaPipe extractor for compatibility.
    
    Args:
        video_path: Path to video file
        max_frames: Optional limit on frames to process
        frame_step: Process every Nth frame (1=all, 2=every other, etc.)
    
    Returns:
        List of PoseFrame dicts with 'frame_index', 'timestamp_sec', 'landmarks'
    """
    model = get_yolo_model()
    if model is None:
        raise RuntimeError("YOLOv8-pose not available. Install with: pip install ultralytics")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if fps <= 0:
        fps = 30.0
    
    frames: List[PoseFrame] = []
    frame_index = 0
    
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            
            if max_frames is not None and frame_index >= max_frames:
                break
            
            # Only process every Nth frame
            if frame_index % frame_step == 0:
                try:
                    # Run YOLO pose estimation (returns Results object)
                    results = model(frame, verbose=False)[0]
                    
                    if results.keypoints is not None and len(results.keypoints) > 0:
                        # Get keypoints for first detected person
                        # Shape: (num_detections, 17, 3) where 3 = x, y, conf
                        keypoints_all = results.keypoints.data.cpu().numpy()
                        
                        if len(keypoints_all) > 0:
                            # Take the first (or highest confidence) person
                            # If multiple people, pick the one with highest average keypoint confidence
                            if len(keypoints_all) > 1:
                                avg_confs = keypoints_all[:, :, 2].mean(axis=1)
                                best_idx = avg_confs.argmax()
                                keypoints = keypoints_all[best_idx]
                            else:
                                keypoints = keypoints_all[0]
                            
                            # Convert to MediaPipe format
                            landmarks = _coco_to_mediapipe_landmarks(keypoints, width, height)
                            
                            timestamp_sec = frame_index / fps
                            frames.append({
                                "frame_index": frame_index,
                                "timestamp_sec": timestamp_sec,
                                "landmarks": landmarks,
                                "yolo_keypoints": keypoints.tolist(),  # Store original too
                            })
                            
                except Exception as e:
                    logger.warning(f"YOLOv8 inference failed on frame {frame_index}: {e}")
            
            frame_index += 1
            
            if frame_index % 20 == 0:
                logger.info(f"YOLOv8-pose: Processed {frame_index} frames...")
                
    finally:
        cap.release()
    
    if not frames:
        raise RuntimeError("No pose frames extracted with YOLOv8-pose")
    
    logger.info(f"YOLOv8-pose: Extracted {len(frames)} pose frames")
    return frames


def is_yolo_available() -> bool:
    """Check if YOLOv8-pose is available."""
    return YOLO_AVAILABLE



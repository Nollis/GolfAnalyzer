"""
MHR Pipeline

Orchestrator that combines swing phase detection with SAM-3D MHR-70 joint extraction.
Extracts key frames from video and runs SAM-3D on each to get detailed body pose data.

Now uses batch processing to load the model only once for all frames.
"""

import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

from pose.swing_detection import SwingDetector
from pose.types import FramePose
from pose.mhr_sam3d_client import (
    run_sam3d_batch,
    run_sam3d_on_image,
    is_sam3d_available,
    is_batch_available
)
from video.frame_extractor import save_frame

logger = logging.getLogger(__name__)


def analyze_with_mhr(
    video_path: Path,
    poses: List[FramePose],
    fps: float,
    hybrik_frames: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Run MHR-70 joint extraction on key swing frames.
    
    Uses SwingDetector to identify key frames (address, top, impact, finish),
    then extracts those frames and runs SAM-3D on them to get detailed body pose.
    
    Uses batch processing for efficiency - model loads only once.
    
    Args:
        video_path: Path to the video file
        poses: List of FramePose objects (from MediaPipe or HybrIK)
        fps: Frames per second of the video
        hybrik_frames: Optional HybrIK frames for improved phase detection
        
    Returns:
        Dictionary with MHR data for each phase:
        {
            "address": {"frame": int, "joints3d": np.ndarray, "joints2d": np.ndarray, "error": str|None},
            "top": {...},
            "impact": {...},
            "finish": {...}
        }
        
        If SAM-3D is not available or fails, joints will be None and error will be set.
    """
    video_path = Path(video_path)
    
    result: Dict[str, Dict[str, Any]] = {
        "address": {"frame": None, "joints3d": None, "joints2d": None, "error": None},
        "top": {"frame": None, "joints3d": None, "joints2d": None, "error": None},
        "impact": {"frame": None, "joints3d": None, "joints2d": None, "error": None},
        "finish": {"frame": None, "joints3d": None, "joints2d": None, "error": None},
    }
    
    # Check if SAM-3D is available
    if not is_sam3d_available():
        logger.warning("[MHR] SAM-3D is not available (paths not found). Skipping MHR analysis.")
        for phase in result:
            result[phase]["error"] = "SAM-3D not available"
        return result
    
    # Detect swing phases
    detector = SwingDetector()
    phases = detector.detect_swing_phases(poses, fps, hybrik_frames=hybrik_frames)
    
    phase_frames = {
        "address": phases.address_frame,
        "top": phases.top_frame,
        "impact": phases.impact_frame,
        "finish": phases.finish_frame,
    }
    
    logger.info(f"[MHR] Key frames: {phase_frames}")
    
    # Create temp directory manually (don't auto-delete to avoid Windows file lock issues)
    import time
    import shutil
    tmp_path = Path(tempfile.gettempdir()) / f"mhr_{int(time.time())}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Extract all frames first
        image_paths: Dict[str, Path] = {}
        
        for phase_name, frame_idx in phase_frames.items():
            result[phase_name]["frame"] = frame_idx
            
            if frame_idx is None or frame_idx < 0:
                result[phase_name]["error"] = f"Invalid frame index: {frame_idx}"
                logger.warning(f"[MHR] Skipping {phase_name}: invalid frame index {frame_idx}")
                continue
            
            # Extract frame as PNG
            frame_png = tmp_path / f"{phase_name}_{frame_idx}.png"
            
            try:
                logger.info(f"[MHR] Extracting frame {frame_idx} for {phase_name}...")
                save_frame(video_path, frame_idx, frame_png)
                image_paths[phase_name] = frame_png
            except Exception as e:
                result[phase_name]["error"] = f"Frame extraction failed: {str(e)}"
                logger.error(f"[MHR] Failed to extract frame {frame_idx}: {e}")
        
        if not image_paths:
            logger.error("[MHR] No frames extracted successfully")
            return result
        
        logger.info(f"[MHR] Extracted {len(image_paths)} frames, running SAM-3D...")
        
        # Step 2: Run SAM-3D (batch or sequential)
        output_dir = tmp_path / "sam3d_output"
        
        if is_batch_available():
            # Use efficient batch processing (model loads once)
            logger.info("[MHR] Using batch processing mode")
            sam_results = run_sam3d_batch(image_paths, output_dir)
            
            for phase_name, sam_result in sam_results.items():
                result[phase_name]["joints3d"] = sam_result.get("joints3d")
                result[phase_name]["joints2d"] = sam_result.get("joints2d")
                if sam_result.get("error") and not result[phase_name]["error"]:
                    result[phase_name]["error"] = sam_result["error"]
        else:
            # Fallback to sequential processing (less efficient)
            logger.warning("[MHR] Batch script not available, using sequential mode (slower)")
            
            for phase_name, image_path in image_paths.items():
                try:
                    phase_output_dir = output_dir / phase_name
                    sam_result = run_sam3d_on_image(image_path, phase_output_dir)
                    
                    result[phase_name]["joints3d"] = sam_result.get("joints3d")
                    result[phase_name]["joints2d"] = sam_result.get("joints2d")
                    result[phase_name]["error"] = sam_result.get("error")
                    
                except Exception as e:
                    result[phase_name]["error"] = f"SAM-3D failed: {str(e)}"
                    logger.error(f"[MHR] SAM-3D failed for {phase_name}: {e}")
    
    finally:
        # Try to cleanup, but don't fail if files are locked
        try:
            shutil.rmtree(tmp_path, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors on Windows
    
    # Summary logging
    success_count = sum(1 for p in result.values() if p["joints3d"] is not None)
    logger.info(f"[MHR] Analysis complete: {success_count}/4 phases extracted successfully")
    
    for phase_name, data in result.items():
        if data["joints3d"] is not None:
            logger.info(f"[MHR] ✓ {phase_name}: frame {data['frame']}, joints3d {data['joints3d'].shape}")
        elif data["error"]:
            logger.warning(f"[MHR] ✗ {phase_name}: {data['error']}")
    
    return result


def mhr_result_to_serializable(mhr_result: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Convert MHR result to a JSON-serializable format.
    
    Converts numpy arrays to lists for JSON serialization.
    
    Args:
        mhr_result: Result from analyze_with_mhr()
        
    Returns:
        JSON-serializable dictionary
    """
    serializable = {}
    
    for phase_name, data in mhr_result.items():
        serializable[phase_name] = {
            "frame": data.get("frame"),
            "joints3d": data["joints3d"].tolist() if isinstance(data.get("joints3d"), np.ndarray) else None,
            "joints2d": data["joints2d"].tolist() if isinstance(data.get("joints2d"), np.ndarray) else None,
            "error": data.get("error"),
        }
    
    return serializable

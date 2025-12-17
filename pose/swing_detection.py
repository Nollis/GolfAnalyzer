from typing import List, Dict, Any, Optional
import numpy as np
from scipy.signal import savgol_filter

from app.schemas import SwingPhases
from pose.types import FramePose

# Try to import HybrIK key frame detection
try:
    from pose.smpl_extractor import detect_key_frames_smpl
    HYBRIK_AVAILABLE = True
except ImportError:
    HYBRIK_AVAILABLE = False


class SwingDetector:
    def _smooth_savgol(self, data: List[float], window_size: int = 7, poly_order: int = 2) -> np.ndarray:
        """
        Apply Savitzky-Golay filter for smoothing.
        Better at preserving sharp transitions (like impact) than moving average.
        """
        if len(data) < window_size:
            return np.array(data)
        
        # Ensure window_size is odd
        if window_size % 2 == 0:
            window_size += 1
        
        return savgol_filter(data, window_size, poly_order)

    def _smooth_data(self, data: List[float], window_size: int = 5) -> List[float]:
        """Apply simple moving average smoothing (kept for backward compatibility)"""
        if len(data) < window_size:
            return data
        
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            smoothed.append(sum(data[start:end]) / (end - start))
        return smoothed

    def detect_swing_phases(self, poses: List[FramePose], fps: float, hybrik_frames: Optional[List[Dict[str, Any]]] = None) -> SwingPhases:
        """
        Detects the key phases of the golf swing using improved heuristics.
        
        Strategy:
        - Address: First stable position (max Y before backswing)
        - Top: First local minimum (hands highest) after significant rise
        - Impact: Maximum Y (hands lowest) in downswing, confirmed by velocity peak
        - Finish: Hands highest after impact
        
        Args:
            poses: List of FramePose objects (MediaPipe format)
            fps: Frames per second
            hybrik_frames: Optional list of HybrIK SMPL frames (preferred if available)
        
        Returns:
            SwingPhases with address, top, impact, finish frame indices
        """
        if not poses:
            return SwingPhases(address_frame=0, top_frame=0, impact_frame=0, finish_frame=0)
        
        # Use HybrIK key frame detection if available (more accurate)
        if HYBRIK_AVAILABLE and hybrik_frames:
            try:
                key_frames = detect_key_frames_smpl(hybrik_frames)
                address_idx = key_frames.get("address_idx", 0)
                top_idx = key_frames.get("top_idx", 0)
                impact_idx = key_frames.get("impact_idx", 0)
                
                # Find finish frame (highest point after impact)
                finish_idx = len(poses) - 1
                if impact_idx < len(poses):
                    wrist_ys = []
                    for i in range(impact_idx + 1, len(poses)):
                        if len(poses[i].landmarks) > 16:
                            ly = poses[i].landmarks[15].y
                            ry = poses[i].landmarks[16].y
                            wrist_ys.append((ly + ry) / 2.0)
                        else:
                            wrist_ys.append(0.5)
                    
                    if wrist_ys:
                        smooth_ys = self._smooth_savgol(wrist_ys, window_size=5)
                        min_idx = int(np.argmin(smooth_ys))
                        finish_idx = impact_idx + 1 + min_idx
                        finish_idx = min(finish_idx, len(poses) - 1)
                
                return SwingPhases(
                    address_frame=max(0, address_idx),
                    top_frame=max(0, top_idx),
                    impact_frame=max(0, impact_idx),
                    finish_frame=max(0, finish_idx)
                )
            except Exception as e:
                # Fall back to MediaPipe detection if HybrIK fails
                print(f"HybrIK key frame detection failed: {e}, falling back to improved heuristics")
        
        # Fallback to improved heuristic-based detection
        # Extract wrist heights (y) - MediaPipe: y increases downwards (0 is top)
        wrist_ys = []
        
        for pose in poses:
            if len(pose.landmarks) > 16:
                ly = pose.landmarks[15].y
                ry = pose.landmarks[16].y
                wrist_ys.append((ly + ry) / 2.0)
            else:
                # Fallback to previous or default
                last_y = wrist_ys[-1] if wrist_ys else 0.5
                wrist_ys.append(last_y)

        total_frames = len(poses)
        if total_frames < 10:
            return SwingPhases(address_frame=0, top_frame=0, impact_frame=0, finish_frame=0)
        
        # Apply Savgol smoothing (better for preserving peaks than moving average)
        smooth_ys = self._smooth_savgol(wrist_ys, window_size=7, poly_order=2)
        
        # Calculate velocity and smooth it for cleaner peak detection
        velocity = np.gradient(smooth_ys)
        smooth_velocity = self._smooth_savgol(velocity, window_size=5, poly_order=2)
        
        # === DETECT TOP OF BACKSWING ===
        # Find first significant local minimum (hands at highest point)
        # Velocity crosses from negative (going up) to positive (going down)
        
        address_y = smooth_ys[0]
        threshold_rise = 0.08  # Must rise at least 8% from start
        
        top_frame = 0
        for i in range(5, total_frames - 5):
            # Check for significant rise from address
            if address_y - smooth_ys[i] > threshold_rise:
                # Look for velocity zero-crossing (neg -> pos)
                if velocity[i-1] <= 0 and velocity[i] > 0:
                    # Confirm it's a real peak by checking surrounding values
                    if smooth_ys[i] < smooth_ys[i-3] and smooth_ys[i] < smooth_ys[i+3]:
                        top_frame = i
                        break
        
        # Fallback: find global minimum in first 60% of video
        if top_frame == 0:
            search_end = int(total_frames * 0.6)
            if search_end > 0:
                top_frame = int(np.argmin(smooth_ys[:search_end]))
        
        # === DETECT ADDRESS ===
        # Find the stable low position (max Y) before backswing begins
        address_frame = 0
        search_start = max(0, top_frame - int(fps * 2))  # Up to 2 seconds before top
        
        max_y_before_top = -1.0
        for i in range(search_start, top_frame):
            if smooth_ys[i] > max_y_before_top:
                max_y_before_top = smooth_ys[i]
                address_frame = i
        
        # === DETECT IMPACT ===
        # Impact is when hands reach their LOWEST point (maximum Y) in the downswing
        # Use multiple signals for robustness:
        # 1. Maximum Y value in the downswing window
        # 2. Peak positive velocity (fastest descent)
        
        search_start = top_frame + 3
        search_end = min(total_frames - 5, top_frame + int(fps * 0.5))  # Max 0.5s downswing
        
        if search_end <= search_start:
            search_end = min(total_frames - 1, search_start + 15)
        
        # Method 1: Find maximum Y (hands lowest)
        max_y_downswing = -1.0
        impact_by_position = search_start
        
        for i in range(search_start, search_end):
            if smooth_ys[i] > max_y_downswing:
                max_y_downswing = smooth_ys[i]
                impact_by_position = i
            # Early exit: if hands have risen significantly, we've passed impact
            elif max_y_downswing > 0 and max_y_downswing - smooth_ys[i] > 0.04:
                break
        
        # Method 2: Find peak velocity (maximum positive velocity = fastest descent)
        velocity_window = smooth_velocity[search_start:search_end]
        if len(velocity_window) > 0:
            peak_velocity_idx = int(np.argmax(velocity_window))
            impact_by_velocity = search_start + peak_velocity_idx
        else:
            impact_by_velocity = impact_by_position
        
        # Combine signals: prefer position-based, but validate with velocity
        if abs(impact_by_position - impact_by_velocity) <= 3:
            impact_frame = impact_by_position  # Position is reliable
        else:
            # Use position but adjust slightly toward velocity peak
            impact_frame = int(0.7 * impact_by_position + 0.3 * impact_by_velocity)
        
        # Final adjustment: check if the frame after has an even lower hand position
        # This catches the "off by 1" error
        if impact_frame + 1 < total_frames:
            if smooth_ys[impact_frame + 1] >= smooth_ys[impact_frame]:
                impact_frame = impact_frame + 1
        
        # === DETECT FINISH ===
        # Hands reach highest point (minimum Y) after impact
        finish_frame = total_frames - 1
        min_y_after_impact = 1.0
        
        for i in range(impact_frame + 3, total_frames):
            if smooth_ys[i] < min_y_after_impact:
                min_y_after_impact = smooth_ys[i]
                finish_frame = i

        # === SAFETY CHECKS ===
        # Ensure chronological order
        if top_frame <= address_frame:
            top_frame = address_frame + 5
        if impact_frame <= top_frame:
            impact_frame = top_frame + 5
        if finish_frame <= impact_frame:
            finish_frame = impact_frame + 5
        
        # Clamp to valid range
        finish_frame = min(finish_frame, total_frames - 1)
        impact_frame = min(impact_frame, finish_frame - 1)
        top_frame = min(top_frame, impact_frame - 1)
        address_frame = min(address_frame, top_frame - 1)
        
        return SwingPhases(
            address_frame=max(0, address_frame),
            top_frame=max(0, top_frame),
            impact_frame=max(0, impact_frame),
            finish_frame=max(0, finish_frame)
        )

from typing import List, Dict, Any, Optional
from app.schemas import SwingPhases
from pose.mediapipe_wrapper import FramePose

# Try to import HybrIK key frame detection
try:
    from pose.smpl_extractor import detect_key_frames_smpl
    HYBRIK_AVAILABLE = True
except ImportError:
    HYBRIK_AVAILABLE = False

class SwingDetector:
    def _smooth_data(self, data: List[float], window_size: int = 5) -> List[float]:
        """Apply simple moving average smoothing"""
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
        Detects the key phases of the golf swing.
        
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
                        smooth_ys = self._smooth_data(wrist_ys, window_size=5)
                        min_val = min(smooth_ys)
                        min_idx = smooth_ys.index(min_val)
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
                print(f"HybrIK key frame detection failed: {e}, falling back to MediaPipe")
        
        # Fallback to MediaPipe-based detection

        # Extract wrist heights (y) and lateral position (x)
        # MediaPipe: y increases downwards (0 is top), x increases rightwards
        wrist_ys = []
        wrist_xs = []
        
        for pose in poses:
            if len(pose.landmarks) > 16:
                ly = pose.landmarks[15].y
                ry = pose.landmarks[16].y
                lx = pose.landmarks[15].x
                rx = pose.landmarks[16].x
                wrist_ys.append((ly + ry) / 2.0)
                wrist_xs.append((lx + rx) / 2.0)
            else:
                # Fallback to previous or default
                last_y = wrist_ys[-1] if wrist_ys else 0.5
                last_x = wrist_xs[-1] if wrist_xs else 0.5
                wrist_ys.append(last_y)
                wrist_xs.append(last_x)

        # Smooth the data to remove jitter
        smooth_ys = self._smooth_data(wrist_ys, window_size=5)
        
        total_frames = len(poses)
        
        # Calculate velocity to detect swing phases
        import numpy as np
        velocity = np.gradient(smooth_ys)
        
        # 1. Detect Top of Backswing
        # Strategy: Find the FIRST local minimum (first peak where hands are highest)
        # This avoids confusing backswing top with follow-through high point
        
        # Find local minima using velocity sign changes (going from negative to positive)
        # Negative velocity = hands going UP (Y decreasing)
        # Positive velocity = hands going DOWN (Y increasing)
        local_minima = []
        for i in range(5, total_frames - 5):
            # Look for velocity zero-crossing from negative to positive
            if velocity[i-1] < 0 and velocity[i] >= 0:
                # Confirm it's a real peak by checking surrounding values
                if smooth_ys[i] < smooth_ys[i-5] and smooth_ys[i] < smooth_ys[i+5]:
                    local_minima.append(i)
        
        # Find the first significant local minimum
        # (hands must have risen at least 0.05 normalized units from start)
        top_frame = 0
        start_y = smooth_ys[0] if smooth_ys else 0.5
        
        for min_idx in local_minima:
            # Check if this is a significant backswing (hands rose meaningfully)
            if start_y - smooth_ys[min_idx] > 0.05:
                top_frame = min_idx
                break
        
        # Fallback: if no local minima found, use simple search in first 60%
        if top_frame == 0:
            search_end_idx = int(total_frames * 0.6)
            min_y = 1.0
            for i in range(10, search_end_idx):
                if smooth_ys[i] < min_y:
                    min_y = smooth_ys[i]
                    top_frame = i
                
        # 2. Detect Address
        # Heuristic: Frame with max Y (hands lowest) BEFORE backswing begins
        # Look for the stable position before the first significant upward movement
        address_frame = 0
        max_y_before_top = -1.0
        
        # Only look at the 2 seconds before top (approx 60 frames at 30fps)
        start_search = max(0, top_frame - int(fps * 2))
        
        for i in range(start_search, top_frame):
            if smooth_ys[i] > max_y_before_top:
                max_y_before_top = smooth_ys[i]
                address_frame = i
                
        # 3. Detect Impact
        # Heuristic: After top, impact is when hands reach their LOWEST point (max Y)
        # in the downswing before they start rising again in follow-through
        impact_frame = top_frame + 1
        
        # Search for the max Y (hands lowest) in the downswing
        # Limit search to reasonable downswing duration (0.3-0.5s at 30fps = 10-15 frames)
        search_start = top_frame + 1
        search_limit = min(total_frames, top_frame + int(fps * 0.6))  # Max 0.6s downswing
        
        max_y_after_top = -1.0
        for i in range(search_start, search_limit):
            if smooth_ys[i] > max_y_after_top:
                max_y_after_top = smooth_ys[i]
                impact_frame = i
            elif max_y_after_top > 0 and max_y_after_top - smooth_ys[i] > 0.05:
                # Hands have risen significantly (0.05 units) - we've passed impact
                break
                    
        # 4. Detect Finish
        # Heuristic: Highest point (min y) AFTER Impact
        finish_frame = total_frames - 1
        min_y_after_impact = 1.0
        
        for i in range(impact_frame + 1, total_frames):
            if smooth_ys[i] < min_y_after_impact:
                min_y_after_impact = smooth_ys[i]
                finish_frame = i

        # Safety checks to ensure chronological order
        if top_frame <= address_frame: top_frame = address_frame + 5
        if impact_frame <= top_frame: impact_frame = top_frame + 5
        if finish_frame <= impact_frame: finish_frame = impact_frame + 5
        
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

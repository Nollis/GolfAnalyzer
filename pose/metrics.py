"""
Golf swing metrics computed from pose landmarks using HybrIK 3D pose estimation.

Supports HybrIK/SMPL format (3D) and **MediaPipe landmark format** (2D, 33 landmarks).
Note: this refers to the landmark *schema/indices*; the `mediapipe` Python package is not required.


COORDINATE SYSTEM:
  For 2D (MediaPipe landmark-format / normalized image coordinates):
    - Y = 0 is TOP of image (head level)
    - Y = 1 is BOTTOM of image (feet level)
  
  For 3D (HybrIK/SMPL):
    - Y is down/up (NEGATIVE = up, POSITIVE = down)
    - X is left/right
    - Z is front/back (depth)
    - Root-relative (pelvis at origin, Y=0)
    - Neck has negative Y (above pelvis)
    - Ankles have positive Y (below pelvis)

Key-frame detection:
  - Address: stable frame before backswing with hands low
  - Top: highest hands position (minimum y in both 2D and 3D)
  - Impact: hands return down to ball level
"""

from typing import List, Optional, Dict, Any, Tuple
import math
import numpy as np
from scipy.signal import savgol_filter
# import mediapipe as mp  # Legacy (removed): we keep the MediaPipe landmark schema without the dependency.

from typing import List, Optional, Dict, Any, Tuple
import math
import numpy as np
from scipy.signal import savgol_filter

from app.schemas import SwingMetrics, SwingPhases
from pose.types import FramePose, Point3D

# MediaPipe landmark indices (hardcoded to avoid a runtime `mediapipe` dependency)
# See: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
IDX_NOSE = 0
IDX_L_SHOULDER = 11
IDX_R_SHOULDER = 12
IDX_L_ELBOW = 13
IDX_R_ELBOW = 14
IDX_L_WRIST = 15
IDX_R_WRIST = 16
IDX_L_HIP = 23
IDX_R_HIP = 24
IDX_L_KNEE = 25
IDX_R_KNEE = 26
IDX_L_ANKLE = 27
IDX_R_ANKLE = 28


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _get_xy(pose: FramePose, idx: int) -> Optional[Tuple[float, float]]:
    """Get 2D (x, y) coordinates for a landmark."""
    if idx >= len(pose.landmarks):
        return None
    lm = pose.landmarks[idx]
    return lm.x, lm.y


def _get_xy_from_frame(frame: Dict[str, Any], idx: int) -> Optional[Tuple[float, float]]:
    """Get 2D coordinates from frame dict."""
    landmarks = frame.get("landmarks", [])
    if idx >= len(landmarks):
        return None
    lm = landmarks[idx]
    if isinstance(lm, dict):
        return lm["x"], lm["y"]
    return None


def _get_xyz_from_frame(frame: Dict[str, Any], idx: int) -> Optional[Tuple[float, float, float]]:
    """
    Get 3D (x, y, z) coordinates for a landmark from a pose frame dict.
    
    Priority order:
    1. HybrIK SMPL 3D (landmarks_3d) - True anatomically-constrained 3D
    2. MediaPipe-format landmarks (landmarks) - 2D + optional Z estimate (schema-compatible)
    """
    # Prefer 3D coordinates (from HybrIK)
    landmarks_3d = frame.get("landmarks_3d")
    if landmarks_3d and idx < len(landmarks_3d):
        lm = landmarks_3d[idx]
        if isinstance(lm, dict):
            return lm["x"], lm["y"], lm["z"]
        elif isinstance(lm, (list, tuple)) and len(lm) >= 3:
            return lm[0], lm[1], lm[2]
    
    # Fallback to MediaPipe-format landmarks (2D + optional Z)
    landmarks = frame.get("landmarks", [])
    if idx >= len(landmarks):
        return None
    lm = landmarks[idx]
    if isinstance(lm, dict):
        return lm["x"], lm["y"], lm.get("z", 0.0)
    elif isinstance(lm, (list, tuple)) and len(lm) >= 2:
        return lm[0], lm[1], lm[2] if len(lm) >= 3 else 0.0
    return None


def _get_xyz(pose: FramePose, idx: int) -> Optional[Tuple[float, float, float]]:
    """Get 3D coordinates from FramePose (fallback to 2D + z=0)."""
    if idx >= len(pose.landmarks):
        return None
    lm = pose.landmarks[idx]
    return lm.x, lm.y, lm.z


def _midpoint(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
    return (0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1]))


def _midpoint_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1]), 0.5 * (p1[2] + p2[2]))


def _angle_3d(p1: Tuple, p2: Tuple, p3: Tuple) -> float:
    """
    Calculate the angle at p2 formed by p1-p2-p3 using 3D coordinates.
    
    Works with both 2D (x,y) and 3D (x,y,z) tuples.
    Returns angle in degrees (0-180).
    """
    # Handle both 2D and 3D inputs
    if len(p1) == 2:
        v1 = (p1[0] - p2[0], p1[1] - p2[1], 0)
        v2 = (p3[0] - p2[0], p3[1] - p2[1], 0)
    else:
        v1 = (p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2])
        v2 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2])
    
    # Dot product
    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    
    # Magnitudes
    m1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
    m2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
    
    if m1 == 0 or m2 == 0:
        return 0.0
    
    cos_angle = max(-1.0, min(1.0, dot / (m1 * m2)))
    return math.degrees(math.acos(cos_angle))


def _normalize_angle_diff(angle1: float, angle2: float) -> float:
    """
    Compute the shortest angular difference from angle1 to angle2.
    Returns a value in [-180, 180] representing the rotation.
    """
    diff = angle2 - angle1
    # Normalize to [-180, 180]
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    return diff


def _smooth(values: np.ndarray, max_window: int = 11) -> np.ndarray:
    """Savitzky-Golay smoothing; returns original if too short."""
    n = len(values)
    if n < 5:
        return values
    window = min(max_window, n if n % 2 == 1 else n - 1)
    if window < 5:
        return values
    return savgol_filter(values, window_length=window, polyorder=2)


def _rotation_angle_3d(frame: Dict[str, Any], left_idx: int, right_idx: int) -> Optional[float]:
    """
    Calculate rotation angle in the horizontal (XZ) plane using 3D coordinates.
    
    This measures how much the line between left and right landmarks has rotated
    around the vertical axis (Y). More accurate than 2D for DTL camera angles.
    
    Returns angle in degrees, where:
    - 0° = line perpendicular to camera (facing sideways)
    - 90° = line parallel to camera (facing camera)
    """
    landmarks_3d = frame.get("landmarks_3d")
    if not landmarks_3d or left_idx >= len(landmarks_3d) or right_idx >= len(landmarks_3d):
        return None
    
    l = landmarks_3d[left_idx]
    r = landmarks_3d[right_idx]
    
    # Check visibility (0 = not visible)
    if isinstance(l, dict):
        if l.get("visibility", 0) < 0.5 or r.get("visibility", 0) < 0.5:
            return None
        dx = r['x'] - l['x']
        dz = r['z'] - l['z']
    else:
        dx = r[0] - l[0]
        dz = r[2] - l[2]
    
    return math.degrees(math.atan2(dz, dx))


def _rotation_from_separation_2d(frame: Dict[str, Any], left_idx: int, right_idx: int, 
                                   max_separation: float = 0.06) -> Optional[float]:
    """
    Estimate rotation angle from 2D separation distance (for DTL camera views).
    
    In a DTL (down-the-line) view:
    - When shoulders/hips are perpendicular to camera (address), X separation is minimal
    - When rotated toward/away from camera, X separation increases
    
    For a right-handed golfer in DTL view:
    - At address: shoulders nearly overlapping (dx ≈ 0)
    - At top of backswing: left shoulder moves right (dx < 0, rotated away)
    - At impact/follow-through: right shoulder moves right (dx > 0, rotated through)
    
    Args:
        frame: Pose frame dict
        left_idx: Index of left landmark
        right_idx: Index of right landmark
        max_separation: Expected max X separation at ~90° rotation (observed ~0.05-0.06)
    
    Returns:
        Estimated rotation angle in degrees:
        - Negative = rotated away from camera (backswing)
        - Positive = rotated toward camera (follow-through)
        - 0 = perpendicular to camera (address)
    """
    l = _get_xy_from_frame(frame, left_idx)
    r = _get_xy_from_frame(frame, right_idx)
    
    if not l or not r:
        return None
    
    # Signed X separation: positive when right is to the right of left
    dx = r[0] - l[0]
    
    # Clamp magnitude to max separation
    dx_clamped = max(-max_separation, min(dx, max_separation))
    
    # Convert to rotation angle using arcsin
    # sin(angle) = dx / max_separation
    # This gives us a signed angle:
    # - dx > 0 → positive angle (rotated through/toward camera)
    # - dx < 0 → negative angle (rotated away/backswing)
    ratio = dx_clamped / max_separation
    angle = math.degrees(math.asin(ratio))
    
    return angle


class MetricsCalculator:
    """
    Calculate golf swing metrics from pose data.
    
    Supports both HybrIK (3D SMPL) and MediaPipe (2D) pose estimation.
    """
    
    def compute_metrics(self, poses: List[FramePose], phases: SwingPhases, fps: float) -> SwingMetrics:
        """
        Compute all 10 core metrics from pose frames.
        
        Args:
            poses: List of FramePose objects
            phases: SwingPhases with address, top, impact, finish frame indices
            fps: Frames per second of the video
            
        Returns:
            SwingMetrics with all 10 core metrics
        """
        if not poses:
            return self._empty_metrics()

        # Convert FramePose to dict format for compatibility
        frames = self._poses_to_frames(poses)
        
        # Check if we have 3D data (from whatever source)
        use_hybrik = frames and frames[0].get("landmarks_3d") is not None
        
        # Helper to get pose at specific frame
        def get_frame(frame_idx: int) -> Dict[str, Any]:
            idx = min(max(0, frame_idx), len(frames) - 1)
            return frames[idx]
        
        def get_pose(frame_idx: int) -> FramePose:
            idx = min(max(0, frame_idx), len(poses) - 1)
            return poses[idx]

        address_frame = get_frame(phases.address_frame)
        top_frame = get_frame(phases.top_frame)
        impact_frame = get_frame(phases.impact_frame)
        
        address_pose = get_pose(phases.address_frame)
        top_pose = get_pose(phases.top_frame)
        impact_pose = get_pose(phases.impact_frame)

        # 1. TEMPO
        t_address = address_pose.timestamp_ms / 1000.0  # Convert to seconds
        t_top = top_pose.timestamp_ms / 1000.0
        t_impact = impact_pose.timestamp_ms / 1000.0
        
        backswing_sec = t_top - t_address
        downswing_sec = t_impact - t_top
        tempo_ratio = backswing_sec / downswing_sec if downswing_sec > 0 else 0.0
        
        # 2. CHEST TURN (shoulder turn) - at top
        chest_turn_top = self._compute_chest_turn(address_frame, top_frame, use_hybrik)
        
        # 3. PELVIS TURN (hip turn) - at top
        pelvis_turn_top = self._compute_pelvis_turn(address_frame, top_frame, use_hybrik)
        
        # 4. X-FACTOR - at top
        x_factor_top = abs(chest_turn_top) - abs(pelvis_turn_top)
        
        # 5. SPINE ANGLE - at address and impact
        spine_angle_address = self._compute_spine_angle(address_frame, use_hybrik)
        spine_angle_impact = self._compute_spine_angle(impact_frame, use_hybrik)
        
        # 6. LEAD ARM - at address, top, impact
        lead_arm_address = self._compute_lead_arm(address_frame, use_hybrik)
        lead_arm_top = self._compute_lead_arm(top_frame, use_hybrik)
        lead_arm_impact = self._compute_lead_arm(impact_frame, use_hybrik)
        
        # 7. TRAIL ELBOW - at address, top, impact
        trail_elbow_address = self._compute_trail_elbow(address_frame, use_hybrik)
        trail_elbow_top = self._compute_trail_elbow(top_frame, use_hybrik)
        trail_elbow_impact = self._compute_trail_elbow(impact_frame, use_hybrik)
        
        # 8. KNEE FLEX - at address
        knee_flex_left, knee_flex_right = self._compute_knee_flex(address_frame, use_hybrik)
        
        # 9. HEAD SWAY - range across entire swing
        head_sway_range = self._compute_head_sway_range(frames)
        
        # 10. EARLY EXTENSION - amount
        early_extension = self._compute_early_extension(address_frame, impact_frame)
        
        # 11. SWING PATH INDEX - shallow vs over-the-top
        # Detect handedness first
        handedness = "Right"  # Default, could be made dynamic later
        swing_path_index = self._compute_swing_path_index(
            frames, 
            phases.top_frame, 
            phases.impact_frame,
            handedness
        )

        # 12. HAND HEIGHT AT TOP (DTL)
        hand_height_index = self._compute_hand_height(top_frame, handedness, use_hybrik)

        # 13. HAND WIDTH AT TOP (DTL)
        hand_width_index = self._compute_hand_width(top_frame, handedness, use_hybrik)

        # 14. VERTICAL HEAD MOVEMENT (Refined)
        head_vert = self._compute_vertical_head_movement(address_frame, top_frame, impact_frame, use_hybrik)
        
        # Helper function to safely round values (handle None)
        def safe_round(value, decimals=1):
            if value is None:
                return None
            return round(value, decimals)
        
        return SwingMetrics(
            tempo_ratio=safe_round(tempo_ratio, 2),
            backswing_duration_ms=safe_round(backswing_sec * 1000, 0) if backswing_sec is not None else None,
            downswing_duration_ms=safe_round(downswing_sec * 1000, 0) if downswing_sec is not None else None,
            chest_turn_top_deg=safe_round(abs(chest_turn_top), 1) if chest_turn_top is not None else None,
            pelvis_turn_top_deg=safe_round(abs(pelvis_turn_top), 1) if pelvis_turn_top is not None else None,
            x_factor_top_deg=safe_round(x_factor_top, 1) if x_factor_top is not None else None,
            spine_angle_address_deg=safe_round(spine_angle_address, 1) if spine_angle_address is not None else None,
            spine_angle_impact_deg=safe_round(spine_angle_impact, 1) if spine_angle_impact is not None else None,
            lead_arm_address_deg=safe_round(lead_arm_address, 1) if lead_arm_address is not None else None,
            lead_arm_top_deg=safe_round(lead_arm_top, 1) if lead_arm_top is not None else None,
            lead_arm_impact_deg=safe_round(lead_arm_impact, 1) if lead_arm_impact is not None else None,
            trail_elbow_address_deg=safe_round(trail_elbow_address, 1) if trail_elbow_address is not None else None,
            trail_elbow_top_deg=safe_round(trail_elbow_top, 1) if trail_elbow_top is not None else None,
            trail_elbow_impact_deg=safe_round(trail_elbow_impact, 1) if trail_elbow_impact is not None else None,
            knee_flex_left_address_deg=safe_round(knee_flex_left, 1) if knee_flex_left is not None else None,
            knee_flex_right_address_deg=safe_round(knee_flex_right, 1) if knee_flex_right is not None else None,
            head_sway_range=safe_round(head_sway_range, 4) if head_sway_range is not None else None,
            early_extension_amount=safe_round(early_extension, 4) if early_extension is not None else None,
            swing_path_index=safe_round(swing_path_index, 3) if swing_path_index is not None else None,
            hand_height_at_top_index=safe_round(hand_height_index, 3) if hand_height_index is not None else None,
            hand_width_at_top_index=safe_round(hand_width_index, 3) if hand_width_index is not None else None,
            head_drop_cm=safe_round(head_vert.get("drop_cm"), 1),
            head_rise_cm=safe_round(head_vert.get("rise_cm"), 1),
            # Backward compatibility
            shoulder_turn_top_deg=safe_round(abs(chest_turn_top), 1) if chest_turn_top is not None else None,
            hip_turn_top_deg=safe_round(abs(pelvis_turn_top), 1) if pelvis_turn_top is not None else None,
            spine_tilt_address_deg=safe_round(spine_angle_address, 1) if spine_angle_address is not None else None,
            spine_tilt_impact_deg=safe_round(spine_angle_impact, 1) if spine_angle_impact is not None else None,
        )
    
    def _poses_to_frames(self, poses: List[FramePose]) -> List[Dict[str, Any]]:
        """Convert FramePose list to dict format for HybrIK compatibility."""
        frames = []
        for pose in poses:
            frame = {
                "frame_index": pose.frame_index,
                "timestamp_sec": pose.timestamp_ms / 1000.0,
                "landmarks": [
                    {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                    for lm in pose.landmarks
                ]
            }
            frames.append(frame)
        return frames
    
    def _compute_chest_turn(self, address_frame: Dict[str, Any], top_frame: Dict[str, Any], use_3d: bool) -> float:
        """Compute chest (shoulder) turn from address to top."""
        if use_3d:
            addr_angle = _rotation_angle_3d(address_frame, IDX_L_SHOULDER, IDX_R_SHOULDER)
            top_angle = _rotation_angle_3d(top_frame, IDX_L_SHOULDER, IDX_R_SHOULDER)
            if addr_angle is not None and top_angle is not None:
                return _normalize_angle_diff(addr_angle, top_angle)
        
        # Fallback to 2D separation-based estimation
        # max_separation ~0.05-0.06 observed for shoulders at ~90° rotation
        addr_angle = _rotation_from_separation_2d(address_frame, IDX_L_SHOULDER, IDX_R_SHOULDER, max_separation=0.055)
        top_angle = _rotation_from_separation_2d(top_frame, IDX_L_SHOULDER, IDX_R_SHOULDER, max_separation=0.055)
        
        if addr_angle is not None and top_angle is not None:
            return _normalize_angle_diff(addr_angle, top_angle)
        
        return None
    
    def _compute_pelvis_turn(self, address_frame: Dict[str, Any], top_frame: Dict[str, Any], use_3d: bool) -> Optional[float]:
        """Compute pelvis (hip) turn from address to top."""
        if use_3d:
            addr_angle = _rotation_angle_3d(address_frame, IDX_L_HIP, IDX_R_HIP)
            top_angle = _rotation_angle_3d(top_frame, IDX_L_HIP, IDX_R_HIP)
            if addr_angle is not None and top_angle is not None:
                return _normalize_angle_diff(addr_angle, top_angle)
        
        # Fallback to 2D separation-based estimation
        # max_separation for hips is slightly larger (~0.07)
        addr_angle = _rotation_from_separation_2d(address_frame, IDX_L_HIP, IDX_R_HIP, max_separation=0.07)
        top_angle = _rotation_from_separation_2d(top_frame, IDX_L_HIP, IDX_R_HIP, max_separation=0.07)
        
        if addr_angle is not None and top_angle is not None:
            return _normalize_angle_diff(addr_angle, top_angle)
            
        return None
    
    def _compute_spine_angle(self, frame: Dict[str, Any], use_3d: bool) -> Optional[float]:
        """Compute spine forward bend angle."""
        if use_3d:
            ls = _get_xyz_from_frame(frame, IDX_L_SHOULDER)
            rs = _get_xyz_from_frame(frame, IDX_R_SHOULDER)
            lh = _get_xyz_from_frame(frame, IDX_L_HIP)
            rh = _get_xyz_from_frame(frame, IDX_R_HIP)
            
            if None not in (ls, rs, lh, rh):
                mid_sh = _midpoint_3d(ls, rs)
                mid_hip = _midpoint_3d(lh, rh)
                
                # Spine vector (hips to shoulders)
                spine_vec = (
                    mid_sh[0] - mid_hip[0],
                    mid_sh[1] - mid_hip[1],  # Negative = up in HybrIK
                    mid_sh[2] - mid_hip[2],
                )
                
                # Vertical vector relative to pelvic tilt? 
                # Simpler: Angle with global Y axis (vertical)
                # In 3D (Y down), vertical is (0, -1, 0) or (0, 1, 0) depending on ref.
                # Assuming Y is down, "up" is (0, -1, 0).
                vertical = (0, -1, 0)
                
                # Angle
                dot = spine_vec[0] * vertical[0] + spine_vec[1] * vertical[1] + spine_vec[2] * vertical[2]
                spine_length = math.sqrt(spine_vec[0]**2 + spine_vec[1]**2 + spine_vec[2]**2)
                
                if spine_length > 0.001:
                    cos_angle = dot / spine_length
                    cos_angle = max(-1.0, min(1.0, cos_angle))
                    return math.degrees(math.acos(cos_angle))
        
        # Fallback to 2D
        ls = _get_xy_from_frame(frame, IDX_L_SHOULDER)
        rs = _get_xy_from_frame(frame, IDX_R_SHOULDER)
        lh = _get_xy_from_frame(frame, IDX_L_HIP)
        rh = _get_xy_from_frame(frame, IDX_R_HIP)
        
        if None not in (ls, rs, lh, rh):
            mid_sh = _midpoint(ls, rs)
            mid_hip = _midpoint(lh, rh)
            dx = mid_sh[0] - mid_hip[0]
            dy = mid_sh[1] - mid_hip[1]
            return math.degrees(math.atan2(abs(dx), -dy))
        
        return None
    
    def _compute_lead_arm(self, frame: Dict[str, Any], use_3d: bool) -> Optional[float]:
        """Compute lead arm angle (elbow angle, 180° = straight)."""
        shoulder = _get_xyz_from_frame(frame, IDX_L_SHOULDER) if use_3d else _get_xy_from_frame(frame, IDX_L_SHOULDER)
        elbow = _get_xyz_from_frame(frame, IDX_L_ELBOW) if use_3d else _get_xy_from_frame(frame, IDX_L_ELBOW)
        wrist = _get_xyz_from_frame(frame, IDX_L_WRIST) if use_3d else _get_xy_from_frame(frame, IDX_L_WRIST)
        
        if None in (shoulder, elbow, wrist):
            return None
        
        return _angle_3d(shoulder, elbow, wrist)
    
    def _compute_trail_elbow(self, frame: Dict[str, Any], use_3d: bool) -> Optional[float]:
        """Compute trail elbow angle."""
        shoulder = _get_xyz_from_frame(frame, IDX_R_SHOULDER) if use_3d else _get_xy_from_frame(frame, IDX_R_SHOULDER)
        elbow = _get_xyz_from_frame(frame, IDX_R_ELBOW) if use_3d else _get_xy_from_frame(frame, IDX_R_ELBOW)
        wrist = _get_xyz_from_frame(frame, IDX_R_WRIST) if use_3d else _get_xy_from_frame(frame, IDX_R_WRIST)
        
        if None in (shoulder, elbow, wrist):
            return None
        
        return _angle_3d(shoulder, elbow, wrist)
    
    def _compute_knee_flex(self, frame: Dict[str, Any], use_3d: bool) -> Tuple[Optional[float], Optional[float]]:
        """Compute knee flex angles (left, right) at address."""
        l_hip = _get_xyz_from_frame(frame, IDX_L_HIP) if use_3d else _get_xy_from_frame(frame, IDX_L_HIP)
        l_knee = _get_xyz_from_frame(frame, IDX_L_KNEE) if use_3d else _get_xy_from_frame(frame, IDX_L_KNEE)
        l_ankle = _get_xyz_from_frame(frame, IDX_L_ANKLE) if use_3d else _get_xy_from_frame(frame, IDX_L_ANKLE)
        
        r_hip = _get_xyz_from_frame(frame, IDX_R_HIP) if use_3d else _get_xy_from_frame(frame, IDX_R_HIP)
        r_knee = _get_xyz_from_frame(frame, IDX_R_KNEE) if use_3d else _get_xy_from_frame(frame, IDX_R_KNEE)
        r_ankle = _get_xyz_from_frame(frame, IDX_R_ANKLE) if use_3d else _get_xy_from_frame(frame, IDX_R_ANKLE)
        
        left_angle = _angle_3d(l_hip, l_knee, l_ankle) if None not in (l_hip, l_knee, l_ankle) else None
        right_angle = _angle_3d(r_hip, r_knee, r_ankle) if None not in (r_hip, r_knee, r_ankle) else None
        
        return left_angle, right_angle
    
    def _compute_head_sway_range(self, frames: List[Dict[str, Any]]) -> Optional[float]:
        """Compute head sway range across entire swing."""
        xs = []
        for frame in frames:
            nose = _get_xy_from_frame(frame, IDX_NOSE)
            if nose:
                xs.append(nose[0])
        
        if len(xs) < 2:
            return None
        
        x_arr = _smooth(np.array(xs))
        return float(np.nanmax(x_arr) - np.nanmin(x_arr))
    
    def _compute_early_extension(self, address_frame: Dict[str, Any], impact_frame: Dict[str, Any]) -> Optional[float]:
        """Compute early extension amount (hip movement toward ball)."""
        addr_lh = _get_xy_from_frame(address_frame, IDX_L_HIP)
        addr_rh = _get_xy_from_frame(address_frame, IDX_R_HIP)
        imp_lh = _get_xy_from_frame(impact_frame, IDX_L_HIP)
        imp_rh = _get_xy_from_frame(impact_frame, IDX_R_HIP)
        
        if None in (addr_lh, addr_rh, imp_lh, imp_rh):
            return None
        
        addr_y = (addr_lh[1] + addr_rh[1]) / 2
        imp_y = (imp_lh[1] + imp_rh[1]) / 2
        
        # Early extension = hips moving toward ball (Y decreasing)
        return addr_y - imp_y
    
    def _compute_swing_path_index(
        self, 
        frames: List[Dict[str, Any]], 
        top_frame_idx: int, 
        impact_frame_idx: int,
        handedness: str = "Right"
    ) -> Optional[float]:
        """
        Compute swing path index to detect shallow vs over-the-top.
        
        Measures lateral (X-axis) movement of lead wrist at transition.
        - Negative value = shallow (wrist moves inward toward body) ✓
        - Positive value = over-the-top (wrist moves outward toward target) ✗
        
        Args:
            frames: List of pose frames with 3D landmarks
            top_frame_idx: Frame index of top of backswing
            impact_frame_idx: Frame index of impact
            handedness: "Right" or "Left" handed golfer
            
        Returns:
            swing_path_index: Normalized lateral displacement (-1 to +1 typical range)
        """
        if not frames or top_frame_idx >= len(frames) or impact_frame_idx >= len(frames):
            return None
            
        # Determine lead wrist index based on handedness
        # For right-handed: lead arm is LEFT arm
        # For left-handed: lead arm is RIGHT arm
        lead_wrist_idx = IDX_L_WRIST if handedness == "Right" else IDX_R_WRIST
        
        # Get wrist position at top of backswing
        top_frame = frames[top_frame_idx]
        top_wrist = _get_xyz_from_frame(top_frame, lead_wrist_idx)
        
        if top_wrist is None:
            return None
            
        # Calculate transition frame (20% into downswing)
        downswing_frames = impact_frame_idx - top_frame_idx
        if downswing_frames <= 2:
            return None
            
        transition_offset = max(2, int(downswing_frames * 0.2))
        transition_frame_idx = min(top_frame_idx + transition_offset, impact_frame_idx - 1)
        
        transition_frame = frames[transition_frame_idx]
        transition_wrist = _get_xyz_from_frame(transition_frame, lead_wrist_idx)
        
        if transition_wrist is None:
            return None
            
        # Calculate lateral displacement (X-axis movement)
        # In DTL view: positive X = toward target, negative X = toward body
        x_displacement = transition_wrist[0] - top_wrist[0]
        
        # For right-handed golfer in DTL view:
        # - If wrist moves LEFT (negative X) at transition, that's shallow (good)
        # - If wrist moves RIGHT (positive X) at transition, that's over-the-top (bad)
        # 
        # We want: negative = shallow (good), positive = over-the-top (bad)
        # So for right-handed: return x_displacement directly
        # For left-handed: mirror it
        if handedness == "Left":
            x_displacement = -x_displacement
            
        # Normalize by approximate body width for scale independence
        # Get shoulder width as reference
        l_shoulder = _get_xyz_from_frame(top_frame, IDX_L_SHOULDER)
        r_shoulder = _get_xyz_from_frame(top_frame, IDX_R_SHOULDER)
        
        if l_shoulder is not None and r_shoulder is not None:
            shoulder_width = abs(l_shoulder[0] - r_shoulder[0])
            if shoulder_width > 0.01:
                # Normalize: typical good shallow is about -0.3 to -0.5 of shoulder width
                return x_displacement / shoulder_width
        
        # Fallback: return raw displacement (approximate normalization)
        return x_displacement * 5  # Scale to similar range
    
    def _compute_hand_height(self, frame: Dict[str, Any], handedness: str, use_3d: bool) -> Optional[float]:
        """
        Compute normalized hand height at top.
        Index > 0: Hands above shoulder (High)
        Index < 0: Hands below shoulder (Low/Flat)
        """
        lead_wrist_idx = IDX_L_WRIST if handedness == "Right" else IDX_R_WRIST
        lead_shoulder_idx = IDX_L_SHOULDER if handedness == "Right" else IDX_R_SHOULDER
        
        wrist = _get_xyz_from_frame(frame, lead_wrist_idx) if use_3d else _get_xy_from_frame(frame, lead_wrist_idx)
        shoulder = _get_xyz_from_frame(frame, lead_shoulder_idx) if use_3d else _get_xy_from_frame(frame, lead_shoulder_idx)
        
        if not wrist or not shoulder:
            return None
            
        # Y is down in both systems (usually), but verify coordinate system text
        # HybrIK: NEGATIVE = up. MediaPipe: 0 = top.
        # So "Above" shoulder means wrist.y < shoulder.y
        # We want Positive index for High (Above).
        # Diff = shoulder.y - wrist.y
        # If wrist(0.2) < shoulder(0.5) -> Diff = 0.3 (Positive/High)
        diff = shoulder[1] - wrist[1]
        
        # Normalize by torso length (roughly shoulder to hip)
        l_sh = _get_xyz_from_frame(frame, IDX_L_SHOULDER) if use_3d else _get_xy_from_frame(frame, IDX_L_SHOULDER)
        l_hip = _get_xyz_from_frame(frame, IDX_L_HIP) if use_3d else _get_xy_from_frame(frame, IDX_L_HIP)
        
        if l_sh and l_hip:
            torso_len = abs(l_sh[1] - l_hip[1])
            if torso_len > 0.01:
                return diff / torso_len
                
        return diff * 2.0 # Fallback scale

    def _compute_hand_width(self, frame: Dict[str, Any], handedness: str, use_3d: bool) -> Optional[float]:
        """
        Compute normalized hand width (distance from chest) at top.
        Higher index = Wider/More disconnected
        """
        lead_wrist_idx = IDX_L_WRIST if handedness == "Right" else IDX_R_WRIST
        
        wrist = _get_xyz_from_frame(frame, lead_wrist_idx) if use_3d else _get_xy_from_frame(frame, lead_wrist_idx)
        l_sh = _get_xyz_from_frame(frame, IDX_L_SHOULDER) if use_3d else _get_xy_from_frame(frame, IDX_L_SHOULDER)
        r_sh = _get_xyz_from_frame(frame, IDX_R_SHOULDER) if use_3d else _get_xy_from_frame(frame, IDX_R_SHOULDER)
        
        if not wrist or not l_sh or not r_sh:
            return None
            
        # Chest Midpoint
        if len(l_sh) == 3:
            chest = ((l_sh[0]+r_sh[0])/2, (l_sh[1]+r_sh[1])/2, (l_sh[2]+r_sh[2])/2)
            # Distance 3D
            dist = math.sqrt((wrist[0]-chest[0])**2 + (wrist[1]-chest[1])**2 + (wrist[2]-chest[2])**2)
        else:
            chest = ((l_sh[0]+r_sh[0])/2, (l_sh[1]+r_sh[1])/2)
            # Distance 2D
            dist = math.sqrt((wrist[0]-chest[0])**2 + (wrist[1]-chest[1])**2)
            
        # Normalize by shoulder width
        if len(l_sh) == 3:
            sh_width = math.sqrt((l_sh[0]-r_sh[0])**2 + (l_sh[1]-r_sh[1])**2 + (l_sh[2]-r_sh[2])**2)
        else:
            sh_width = math.sqrt((l_sh[0]-r_sh[0])**2 + (l_sh[1]-r_sh[1])**2)
            
        if sh_width > 0.01:
            return dist / sh_width
            
        if l_hip and r_hip and l_sh and r_sh:
             # Calculate torso width/depth to normalize?
             # For now, approximate based on shoulder width
             shoulder_width = abs(l_sh[0] - r_sh[0])
             if shoulder_width > 0.01:
                 return diff / shoulder_width
                 
        return diff * 2.5 # Fallback scale

    def _compute_vertical_head_movement(
        self, 
        address_frame: Dict[str, Any], 
        top_frame: Dict[str, Any], 
        impact_frame: Dict[str, Any],
        use_3d: bool
    ) -> Dict[str, float]:
        """
        Compute vertical head movement in cm (approx).
        
        - Drop: Distance head moves DOWN from Address to Top.
        - Rise: Distance head moves UP from Top to Impact.
        
        Returns:
            Dict with "drop_cm" and "rise_cm".
        """
        addr_nose = _get_xyz_from_frame(address_frame, IDX_NOSE) if use_3d else _get_xy_from_frame(address_frame, IDX_NOSE)
        top_nose = _get_xyz_from_frame(top_frame, IDX_NOSE) if use_3d else _get_xy_from_frame(top_frame, IDX_NOSE)
        imp_nose = _get_xyz_from_frame(impact_frame, IDX_NOSE) if use_3d else _get_xy_from_frame(impact_frame, IDX_NOSE)
        
        if not addr_nose or not top_nose or not imp_nose:
            return {"drop_cm": 0.0, "rise_cm": 0.0}
            
        # Determine scale factor (pixels/units to cm)
        # Use Torso Length = approx 50cm
        scale_cm_per_unit = 100.0 # Default fallback
        
        l_sh = _get_xyz_from_frame(address_frame, IDX_L_SHOULDER) if use_3d else _get_xy_from_frame(address_frame, IDX_L_SHOULDER)
        l_hip = _get_xyz_from_frame(address_frame, IDX_L_HIP) if use_3d else _get_xy_from_frame(address_frame, IDX_L_HIP)
        
        if l_sh and l_hip:
            torso_len_units = abs(l_sh[1] - l_hip[1]) # Y diff
            if torso_len_units > 0.01:
                # Average torso length is ~50cm
                scale_cm_per_unit = 50.0 / torso_len_units
                
        # Calculate Y differences. 
        # CAUTION: Coordinate systems vary.
        # MediaPipe: Y=0 is TOP. Down = Positive Y.
        # So Lower Head = Higher Y value.
        # HybrIK: Y usually Down in image space too? 
        # Assuming Y increases DOWNWARDS (standard image coords).
        
        # Drop (Address -> Top): Head goes DOWN. Y increases.
        # Drop = Top.y - Address.y
        drop_units = top_nose[1] - addr_nose[1]
        
        # Rise (Top -> Impact): Head goes UP. Y decreases.
        # Rise = Top.y - Impact.y (Positive if Impact is higher/smaller Y than Top)
        # Or Rise = (Max Y during swing) - Impact Y? 
        # Let's stick to Top -> Impact delta.
        # If Impact head is HIGHER than Top head: Top.y > Impact.y
        rise_units = top_nose[1] - imp_nose[1]
        
        drop_cm = drop_units * scale_cm_per_unit
        rise_cm = rise_units * scale_cm_per_unit
        
        return {
            "drop_cm": drop_cm,
            "rise_cm": rise_cm
        }

    
    def _empty_metrics(self) -> SwingMetrics:
        """Return empty metrics with all None (defaults)."""
        return SwingMetrics(
            # All fields default to None in schema
        )

    def detect_handedness(self, poses: List[FramePose], phases: SwingPhases) -> str:
        """Detect if golfer is Right or Left handed."""
        if not poses:
            return "Right"

        address_pose = poses[phases.address_frame]
        top_pose = poses[phases.top_frame]
        
        def get_wrist_x(pose: FramePose):
            lw = pose.landmarks[IDX_L_WRIST]
            rw = pose.landmarks[IDX_R_WRIST]
            return (lw.x + rw.x) / 2
            
        x_address = get_wrist_x(address_pose)
        x_top = get_wrist_x(top_pose)
        
        if x_top < x_address:
            return "Left"
        else:
            return "Right"

    def estimate_club_type(self, metrics: SwingMetrics) -> str:
        """Estimate club type based on swing characteristics."""
        bs_ms = metrics.backswing_duration_ms
        
        if bs_ms > 1000:
            return "Driver"
        elif bs_ms > 800:
            return "Iron"
        else:
            return "Wedge"


def extract_key_frames(poses: List[FramePose], phases: SwingPhases) -> List[Dict[str, Any]]:
    """
    Extract key frames (address, top, impact, finish) with landmarks for skeleton visualization.
    
    Args:
        poses: List of FramePose objects
        phases: SwingPhases with address, top, impact, finish frame indices
        
    Returns:
        List of key frame dicts with frame_index, timestamp_sec, phase, and landmarks
    """
    key_frames = []
    
    for phase_name, frame_idx in [
        ("address", phases.address_frame),
        ("top", phases.top_frame),
        ("impact", phases.impact_frame),
        ("finish", phases.finish_frame),
    ]:
        if 0 <= frame_idx < len(poses):
            pose = poses[frame_idx]
            key_frames.append({
                "frame_index": pose.frame_index,
                "timestamp_sec": pose.timestamp_ms / 1000.0,
                "phase": phase_name,
                "landmarks": [
                    {
                        "x": lm.x,
                        "y": lm.y,
                        "z": lm.z,
                        "visibility": lm.visibility,
                    }
                    for lm in pose.landmarks
                ],
                "smpl_pose": getattr(pose, "smpl_pose", None)
            })
    
    return key_frames

"""
MHR Metrics - Golf swing metrics calculated from SAM-3D MHR-70 3D joints.

Uses true 3D joint positions for accurate rotation measurements,
replacing approximations from 2D pose estimation.
"""

import math
import numpy as np
from typing import Dict, Any, Optional, Tuple


# MHR-70 Joint Indices (from sam-3d-body/sam_3d_body/metadata/mhr70.py)
MHR_NOSE = 0
MHR_L_EYE = 1
MHR_R_EYE = 2
MHR_L_EAR = 3
MHR_R_EAR = 4
MHR_L_SHOULDER = 5
MHR_R_SHOULDER = 6
MHR_L_ELBOW = 7
MHR_R_ELBOW = 8
MHR_L_HIP = 9
MHR_R_HIP = 10
MHR_L_KNEE = 11
MHR_R_KNEE = 12
MHR_L_ANKLE = 13
MHR_R_ANKLE = 14
MHR_R_WRIST = 41
MHR_L_WRIST = 62
MHR_L_ACROMION = 67
MHR_R_ACROMION = 68
MHR_NECK = 69


def _get_joint(joints: np.ndarray, idx: int) -> Optional[np.ndarray]:
    """Get joint position as (x, y, z) array."""
    if joints is None or idx >= len(joints):
        return None
    return joints[idx]


def _midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Get midpoint between two 3D points."""
    return (p1 + p2) / 2


def _angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate angle between two 3D vectors in degrees."""
    v1_norm = np.linalg.norm(v1)
    v2_norm = np.linalg.norm(v2)
    if v1_norm < 1e-6 or v2_norm < 1e-6:
        return 0.0
    cos_angle = np.clip(np.dot(v1, v2) / (v1_norm * v2_norm), -1.0, 1.0)
    return math.degrees(math.acos(cos_angle))


def _rotation_in_xz_plane(p1: np.ndarray, p2: np.ndarray) -> float:
    """
    Calculate rotation angle in the horizontal (XZ) plane.
    
    This measures how the line between p1 and p2 is oriented
    relative to the X-axis when viewed from above.
    
    Returns angle in degrees.
    """
    dx = p2[0] - p1[0]
    dz = p2[2] - p1[2]
    return math.degrees(math.atan2(dz, dx))


def compute_chest_turn(
    addr_joints: np.ndarray, 
    top_joints: np.ndarray
) -> Optional[float]:
    """
    Compute chest (shoulder) rotation from address to top.
    
    Uses XZ plane rotation of shoulder line for true 3D measurement.
    
    Returns rotation in degrees (positive = backswing direction).
    """
    addr_ls = _get_joint(addr_joints, MHR_L_SHOULDER)
    addr_rs = _get_joint(addr_joints, MHR_R_SHOULDER)
    top_ls = _get_joint(top_joints, MHR_L_SHOULDER)
    top_rs = _get_joint(top_joints, MHR_R_SHOULDER)
    
    if any(j is None for j in [addr_ls, addr_rs, top_ls, top_rs]):
        return None
    
    addr_angle = _rotation_in_xz_plane(addr_ls, addr_rs)
    top_angle = _rotation_in_xz_plane(top_ls, top_rs)
    
    diff = top_angle - addr_angle
    # Normalize to [-180, 180]
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    
    return abs(diff)


def compute_pelvis_turn(
    addr_joints: np.ndarray, 
    top_joints: np.ndarray
) -> Optional[float]:
    """
    Compute pelvis (hip) rotation from address to top.
    
    Returns rotation in degrees.
    """
    addr_lh = _get_joint(addr_joints, MHR_L_HIP)
    addr_rh = _get_joint(addr_joints, MHR_R_HIP)
    top_lh = _get_joint(top_joints, MHR_L_HIP)
    top_rh = _get_joint(top_joints, MHR_R_HIP)
    
    if any(j is None for j in [addr_lh, addr_rh, top_lh, top_rh]):
        return None
    
    addr_angle = _rotation_in_xz_plane(addr_lh, addr_rh)
    top_angle = _rotation_in_xz_plane(top_lh, top_rh)
    
    diff = top_angle - addr_angle
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    
    return abs(diff)


def compute_x_factor(
    addr_joints: np.ndarray, 
    top_joints: np.ndarray
) -> Optional[float]:
    """
    Compute X-factor (difference between chest and pelvis turn) at top.
    
    Returns X-factor in degrees.
    """
    chest = compute_chest_turn(addr_joints, top_joints)
    pelvis = compute_pelvis_turn(addr_joints, top_joints)
    
    if chest is None or pelvis is None:
        return None
    
    return abs(chest) - abs(pelvis)


def compute_spine_angle(joints: np.ndarray) -> Optional[float]:
    """
    Compute spine forward bend angle using hip and neck/shoulder midpoints.
    
    Returns angle in degrees from vertical (0 = upright, 30+ = bent forward).
    
    Note: SAM-3D uses Y-down coordinate system (image coordinates).
    """
    lh = _get_joint(joints, MHR_L_HIP)
    rh = _get_joint(joints, MHR_R_HIP)
    neck = _get_joint(joints, MHR_NECK)
    
    if any(j is None for j in [lh, rh]):
        return None
    
    if neck is None:
        # Fallback to shoulder midpoint
        ls = _get_joint(joints, MHR_L_SHOULDER)
        rs = _get_joint(joints, MHR_R_SHOULDER)
        if ls is None or rs is None:
            return None
        upper = _midpoint(ls, rs)
    else:
        upper = neck
    
    hip_mid = _midpoint(lh, rh)
    
    # Spine vector (hip to upper) - points upward in body
    spine = upper - hip_mid
    
    # SAM-3D uses Y-down (image coords), so "up" is negative Y
    # Vertical reference pointing UP (negative Y direction)
    vertical = np.array([0, -1, 0])
    
    angle = _angle_between_vectors(spine, vertical)
    
    # The angle is now the deviation from vertical
    # A person standing upright has spine ≈ (0, -1, 0), angle ≈ 0°
    # A person bent forward 30° has angle ≈ 30°
    return angle


def compute_lead_arm_angle(joints: np.ndarray, handedness: str = "Right") -> Optional[float]:
    """
    Compute lead arm angle (elbow angle, 180° = fully straight).
    
    For right-handed: lead arm is left arm.
    """
    # Normalize handedness to lowercase for case-insensitive comparison
    if handedness.lower() == "right":
        shoulder = _get_joint(joints, MHR_L_SHOULDER)
        elbow = _get_joint(joints, MHR_L_ELBOW)
        wrist = _get_joint(joints, MHR_L_WRIST)
    else:
        shoulder = _get_joint(joints, MHR_R_SHOULDER)
        elbow = _get_joint(joints, MHR_R_ELBOW)
        wrist = _get_joint(joints, MHR_R_WRIST)
    
    if any(j is None for j in [shoulder, elbow, wrist]):
        return None
    
    # Vectors from elbow to shoulder and elbow to wrist
    v1 = shoulder - elbow
    v2 = wrist - elbow
    
    return _angle_between_vectors(v1, v2)


def compute_trail_elbow_angle(joints: np.ndarray, handedness: str = "Right") -> Optional[float]:
    """
    Compute trail elbow angle.
    
    For right-handed: trail arm is right arm.
    """
    # Normalize handedness to lowercase for case-insensitive comparison
    if handedness.lower() == "right":
        shoulder = _get_joint(joints, MHR_R_SHOULDER)
        elbow = _get_joint(joints, MHR_R_ELBOW)
        wrist = _get_joint(joints, MHR_R_WRIST)
    else:
        shoulder = _get_joint(joints, MHR_L_SHOULDER)
        elbow = _get_joint(joints, MHR_L_ELBOW)
        wrist = _get_joint(joints, MHR_L_WRIST)
    
    if any(j is None for j in [shoulder, elbow, wrist]):
        return None
    
    v1 = shoulder - elbow
    v2 = wrist - elbow
    
    return _angle_between_vectors(v1, v2)


def compute_knee_flex(joints: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    """
    Compute knee flex angles (left, right).
    
    Returns (left_angle, right_angle) in degrees. 180° = straight leg.
    """
    lh = _get_joint(joints, MHR_L_HIP)
    lk = _get_joint(joints, MHR_L_KNEE)
    la = _get_joint(joints, MHR_L_ANKLE)
    
    rh = _get_joint(joints, MHR_R_HIP)
    rk = _get_joint(joints, MHR_R_KNEE)
    ra = _get_joint(joints, MHR_R_ANKLE)
    
    left_angle = None
    right_angle = None
    
    if all(j is not None for j in [lh, lk, la]):
        v1 = lh - lk
        v2 = la - lk
        left_angle = _angle_between_vectors(v1, v2)
    
    if all(j is not None for j in [rh, rk, ra]):
        v1 = rh - rk
        v2 = ra - rk
        right_angle = _angle_between_vectors(v1, v2)
    
    return left_angle, right_angle


def compute_head_movement(
    addr_joints: np.ndarray,
    top_joints: np.ndarray,
    impact_joints: np.ndarray
) -> Dict[str, Optional[float]]:
    """
    Compute head movement in 3D.
    
    Note: SAM-3D uses Y-down (image coordinates).
    
    Returns:
        - sway_x: Lateral movement range (cm)
        - drop_y: Vertical drop from address to top (cm, positive = head went down)
        - rise_y: Vertical rise from top to impact (cm, positive = head went up)
    """
    addr_nose = _get_joint(addr_joints, MHR_NOSE)
    top_nose = _get_joint(top_joints, MHR_NOSE)
    imp_nose = _get_joint(impact_joints, MHR_NOSE)
    
    if any(j is None for j in [addr_nose, top_nose, imp_nose]):
        return {"sway_x": None, "drop_y": None, "rise_y": None}
    
    # Estimate scale: torso length ~50cm
    addr_lh = _get_joint(addr_joints, MHR_L_HIP)
    addr_ls = _get_joint(addr_joints, MHR_L_SHOULDER)
    
    scale = 100.0  # Default cm per unit
    if addr_lh is not None and addr_ls is not None:
        torso = np.linalg.norm(addr_ls - addr_lh)
        if torso > 0.01:
            scale = 50.0 / torso  # 50cm typical torso
    
    # Lateral sway (X axis)
    x_range = max(addr_nose[0], top_nose[0], imp_nose[0]) - min(addr_nose[0], top_nose[0], imp_nose[0])
    sway_x = x_range * scale
    
    # Vertical head movement - use absolute Y differences
    # Direction varies by coordinate system, so we use interpretable labels:
    # - drop_y: How much head moved vertically during backswing (abs value)
    # - rise_y: How much head moved vertically from top to impact (abs value)
    
    # Raw Y deltas
    backswing_delta = abs(top_nose[1] - addr_nose[1]) * scale
    downswing_delta = abs(imp_nose[1] - top_nose[1]) * scale
    
    return {
        "sway_x": sway_x,
        "drop_y": backswing_delta,
        "rise_y": downswing_delta
    }


def compute_hand_position(
    joints: np.ndarray, 
    handedness: str = "Right"
) -> Dict[str, Optional[float]]:
    """
    Compute hand position metrics at top of backswing.
    
    Returns:
        - height_index: Hands above/below shoulder (positive = higher)
        - width_index: Distance from chest (larger = wider)
    """
    # Normalize handedness to lowercase for case-insensitive comparison
    if handedness.lower() == "right":
        wrist = _get_joint(joints, MHR_L_WRIST)
        shoulder = _get_joint(joints, MHR_L_SHOULDER)
    else:
        wrist = _get_joint(joints, MHR_R_WRIST)
        shoulder = _get_joint(joints, MHR_R_SHOULDER)
    
    ls = _get_joint(joints, MHR_L_SHOULDER)
    rs = _get_joint(joints, MHR_R_SHOULDER)
    lh = _get_joint(joints, MHR_L_HIP)
    
    if wrist is None or shoulder is None or ls is None or rs is None:
        return {"height_index": None, "width_index": None}
    
    # Height: wrist Y relative to shoulder Y (normalized by torso)
    # SAM-3D uses Y-down: smaller Y = higher position
    # Positive index = hands above shoulder
    if lh is not None:
        torso_len = abs(ls[1] - lh[1])
        if torso_len > 0.01:
            # shoulder.y - wrist.y: positive when wrist is higher (smaller Y)
            height_index = (shoulder[1] - wrist[1]) / torso_len
        else:
            height_index = shoulder[1] - wrist[1]
    else:
        height_index = shoulder[1] - wrist[1]
    
    # Width: 3D distance from chest center
    chest = _midpoint(ls, rs)
    dist = np.linalg.norm(wrist - chest)
    
    # Normalize by shoulder width
    shoulder_width = np.linalg.norm(ls - rs)
    if shoulder_width > 0.01:
        width_index = dist / shoulder_width
    else:
        width_index = dist
    
    return {
        "height_index": height_index,
        "width_index": width_index
    }


def compute_all_mhr_metrics(mhr_data: Dict[str, Dict[str, Any]], handedness: str = "Right") -> Dict[str, Any]:
    """
    Compute all golf metrics from MHR phase data.
    
    Args:
        mhr_data: Dict with 'address', 'top', 'impact', 'finish' keys,
                  each containing 'joints3d' (70, 3) array.
        handedness: "Right" or "Left"
    
    Returns:
        Dict of computed metrics, compatible with SwingMetrics schema.
    """
    addr = mhr_data.get("address", {}).get("joints3d")
    top = mhr_data.get("top", {}).get("joints3d")
    impact = mhr_data.get("impact", {}).get("joints3d")
    finish = mhr_data.get("finish", {}).get("joints3d")
    
    # Convert to numpy arrays if needed
    if addr is not None and not isinstance(addr, np.ndarray):
        addr = np.array(addr)
    if top is not None and not isinstance(top, np.ndarray):
        top = np.array(top)
    if impact is not None and not isinstance(impact, np.ndarray):
        impact = np.array(impact)
    if finish is not None and not isinstance(finish, np.ndarray):
        finish = np.array(finish)
    
    metrics = {}
    
    # Rotation metrics
    if addr is not None and top is not None:
        metrics["chest_turn_top_deg"] = compute_chest_turn(addr, top)
        metrics["pelvis_turn_top_deg"] = compute_pelvis_turn(addr, top)
        metrics["x_factor_top_deg"] = compute_x_factor(addr, top)
    
    # Spine angle
    if addr is not None:
        metrics["spine_angle_address_deg"] = compute_spine_angle(addr)
    if impact is not None:
        metrics["spine_angle_impact_deg"] = compute_spine_angle(impact)
    
    # Arm angles
    if addr is not None:
        metrics["lead_arm_address_deg"] = compute_lead_arm_angle(addr, handedness)
        metrics["trail_elbow_address_deg"] = compute_trail_elbow_angle(addr, handedness)
        knee_l, knee_r = compute_knee_flex(addr)
        metrics["knee_flex_left_address_deg"] = knee_l
        metrics["knee_flex_right_address_deg"] = knee_r
    if top is not None:
        metrics["lead_arm_top_deg"] = compute_lead_arm_angle(top, handedness)
        metrics["trail_elbow_top_deg"] = compute_trail_elbow_angle(top, handedness)
    if impact is not None:
        metrics["lead_arm_impact_deg"] = compute_lead_arm_angle(impact, handedness)
        metrics["trail_elbow_impact_deg"] = compute_trail_elbow_angle(impact, handedness)
    
    # Head movement
    if addr is not None and top is not None and impact is not None:
        head = compute_head_movement(addr, top, impact)
        metrics["head_sway_range"] = head.get("sway_x")
        metrics["head_drop_cm"] = head.get("drop_y")
        metrics["head_rise_cm"] = head.get("rise_y")
    
    # Hand position at top
    if top is not None:
        hand_pos = compute_hand_position(top, handedness)
        metrics["hand_height_at_top_index"] = hand_pos.get("height_index")
        metrics["hand_width_at_top_index"] = hand_pos.get("width_index")
    
    # Convert numpy types to native Python floats for Pydantic serialization
    for key, value in metrics.items():
        if value is not None:
            if isinstance(value, (np.floating, np.float32, np.float64)):
                metrics[key] = float(value)
            elif isinstance(value, (np.integer, np.int32, np.int64)):
                metrics[key] = int(value)
    
    return metrics

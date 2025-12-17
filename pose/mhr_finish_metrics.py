"""
MHR Finish Metrics - Golf swing metrics focused on the FINISH position.

Uses MHR-70 3D joint positions to compute finish balance, rotation,
spine extension, head recovery, and hand position metrics.
"""

import math
import numpy as np
from typing import Dict, Any, Optional, Literal, TypedDict


class PhaseJoints(TypedDict):
    """MHR-70 joints for each swing phase."""
    address: np.ndarray  # (70, 3)
    top: np.ndarray      # (70, 3)
    impact: np.ndarray   # (70, 3)
    finish: np.ndarray   # (70, 3)


# MHR-70 Joint Indices
MHR_NOSE = 0
MHR_L_SHOULDER = 5
MHR_R_SHOULDER = 6
MHR_L_HIP = 9
MHR_R_HIP = 10
MHR_L_HEEL = 17
MHR_R_HEEL = 20
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
    """Calculate rotation angle in the horizontal (XZ) plane."""
    dx = p2[0] - p1[0]
    dz = p2[2] - p1[2]
    return math.degrees(math.atan2(dz, dx))


def _estimate_scale(joints: np.ndarray) -> float:
    """
    Estimate body scale from torso length.
    Returns scale factor to convert to centimeters (approx).
    """
    lh = _get_joint(joints, MHR_L_HIP)
    ls = _get_joint(joints, MHR_L_SHOULDER)
    if lh is None or ls is None:
        return 100.0  # Default scale
    torso_len = np.linalg.norm(ls - lh)
    # Assume average torso is ~50cm
    if torso_len > 0.01:
        return 50.0 / torso_len
    return 100.0


def compute_finish_balance(phase_joints: PhaseJoints) -> Optional[float]:
    """
    Compute finish balance: normalized lateral shift of pelvis toward lead side.
    
    For right-handed golfer:
    - +1 = pelvis fully over lead (left) heel
    - 0 = pelvis under stance center
    - negative = pelvis over trail (right) side
    
    Returns:
        Normalized balance value (-1 to +1), or None if joints missing.
    """
    addr = phase_joints.get("address")
    finish = phase_joints.get("finish")
    
    if addr is None or finish is None:
        return None
    
    # Get heel positions at address (defines stance)
    addr_l_heel = _get_joint(addr, MHR_L_HEEL)
    addr_r_heel = _get_joint(addr, MHR_R_HEEL)
    
    # Get pelvis at finish
    fin_l_hip = _get_joint(finish, MHR_L_HIP)
    fin_r_hip = _get_joint(finish, MHR_R_HIP)
    
    if any(j is None for j in [addr_l_heel, addr_r_heel, fin_l_hip, fin_r_hip]):
        return None
    
    # Stance center in X-Z plane (horizontal)
    stance_center_x = (addr_l_heel[0] + addr_r_heel[0]) / 2
    stance_center_z = (addr_l_heel[2] + addr_r_heel[2]) / 2
    
    # Stance width (for normalization)
    stance_width = abs(addr_l_heel[0] - addr_r_heel[0])
    if stance_width < 0.01:
        stance_width = 0.3  # Default ~30cm
    
    # Pelvis center at finish
    pelvis_x = (fin_l_hip[0] + fin_r_hip[0]) / 2
    
    # Lead heel X (left for right-handed)
    lead_heel_x = addr_l_heel[0]
    
    # Compute normalized lateral shift
    # Positive = toward lead side
    # Note: Negate because SAM-3D X-axis points opposite to our convention
    shift = -(pelvis_x - stance_center_x)
    
    # Normalize: +1 when pelvis over lead heel, 0 at center
    half_stance = stance_width / 2
    if half_stance > 0.01:
        normalized = shift / half_stance
    else:
        normalized = 0.0
    
    return float(np.clip(normalized, -1.0, 1.0))


def compute_finish_spine_extension(phase_joints: PhaseJoints) -> Dict[str, Optional[float]]:
    """
    Compute spine angle to vertical at address, top, and finish.
    
    Returns:
        Dict with spine_angle at each phase and extension from address.
    """
    result = {
        "spine_angle_address_deg": None,
        "spine_angle_top_deg": None,
        "spine_angle_finish_deg": None,
        "extension_from_address_deg": None,
    }
    
    phases = ["address", "top", "finish"]
    angles = {}
    
    for phase in phases:
        joints = phase_joints.get(phase)
        if joints is None:
            continue
        
        # Pelvis center
        l_hip = _get_joint(joints, MHR_L_HIP)
        r_hip = _get_joint(joints, MHR_R_HIP)
        neck = _get_joint(joints, MHR_NECK)
        
        if any(j is None for j in [l_hip, r_hip]):
            continue
        
        pelvis_center = _midpoint(l_hip, r_hip)
        
        if neck is None:
            # Fallback to shoulder midpoint
            l_sh = _get_joint(joints, MHR_L_SHOULDER)
            r_sh = _get_joint(joints, MHR_R_SHOULDER)
            if l_sh is None or r_sh is None:
                continue
            upper = _midpoint(l_sh, r_sh)
        else:
            upper = neck
        
        # Spine vector
        spine = upper - pelvis_center
        
        # Vertical reference (Y-down in SAM-3D, so up is negative Y)
        vertical = np.array([0, -1, 0])
        
        angle = _angle_between_vectors(spine, vertical)
        angles[phase] = angle
        result[f"spine_angle_{phase}_deg"] = round(angle, 2)
    
    # Extension: how much spine straightened from address to finish
    if "address" in angles and "finish" in angles:
        # Positive = more upright at finish
        extension = angles["address"] - angles["finish"]
        result["extension_from_address_deg"] = round(extension, 2)
    
    return result


def compute_finish_rotation(phase_joints: PhaseJoints) -> Dict[str, Optional[float]]:
    """
    Compute chest and pelvis rotation at FINISH relative to address.
    
    Uses acromions (67, 68) for chest and hips (9, 10) for pelvis.
    
    Returns:
        Dict with chest_turn_finish_deg and pelvis_turn_finish_deg.
    """
    result = {
        "chest_turn_finish_deg": None,
        "pelvis_turn_finish_deg": None,
    }
    
    addr = phase_joints.get("address")
    finish = phase_joints.get("finish")
    
    if addr is None or finish is None:
        return result
    
    # Chest rotation (using acromions for more accurate shoulder rotation)
    addr_l_acr = _get_joint(addr, MHR_L_ACROMION)
    addr_r_acr = _get_joint(addr, MHR_R_ACROMION)
    fin_l_acr = _get_joint(finish, MHR_L_ACROMION)
    fin_r_acr = _get_joint(finish, MHR_R_ACROMION)
    
    # Fallback to shoulders if acromions missing
    if any(j is None for j in [addr_l_acr, addr_r_acr, fin_l_acr, fin_r_acr]):
        addr_l_acr = _get_joint(addr, MHR_L_SHOULDER)
        addr_r_acr = _get_joint(addr, MHR_R_SHOULDER)
        fin_l_acr = _get_joint(finish, MHR_L_SHOULDER)
        fin_r_acr = _get_joint(finish, MHR_R_SHOULDER)
    
    if all(j is not None for j in [addr_l_acr, addr_r_acr, fin_l_acr, fin_r_acr]):
        addr_chest_angle = _rotation_in_xz_plane(addr_l_acr, addr_r_acr)
        fin_chest_angle = _rotation_in_xz_plane(fin_l_acr, fin_r_acr)
        diff = fin_chest_angle - addr_chest_angle
        # Normalize to [-180, 180]
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        result["chest_turn_finish_deg"] = round(abs(diff), 2)
    
    # Pelvis rotation
    addr_l_hip = _get_joint(addr, MHR_L_HIP)
    addr_r_hip = _get_joint(addr, MHR_R_HIP)
    fin_l_hip = _get_joint(finish, MHR_L_HIP)
    fin_r_hip = _get_joint(finish, MHR_R_HIP)
    
    if all(j is not None for j in [addr_l_hip, addr_r_hip, fin_l_hip, fin_r_hip]):
        addr_pelvis_angle = _rotation_in_xz_plane(addr_l_hip, addr_r_hip)
        fin_pelvis_angle = _rotation_in_xz_plane(fin_l_hip, fin_r_hip)
        diff = fin_pelvis_angle - addr_pelvis_angle
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        result["pelvis_turn_finish_deg"] = round(abs(diff), 2)
    
    return result


def compute_head_recovery(phase_joints: PhaseJoints) -> Dict[str, Optional[float]]:
    """
    Compute head movement from top to finish.
    
    Returns:
        - head_rise_top_to_finish_cm: Vertical movement (positive = rose)
        - head_lateral_shift_address_to_finish_cm: Lateral movement
    """
    result = {
        "head_rise_top_to_finish_cm": None,
        "head_lateral_shift_address_to_finish_cm": None,
    }
    
    addr = phase_joints.get("address")
    top = phase_joints.get("top")
    finish = phase_joints.get("finish")
    
    if addr is None or top is None or finish is None:
        return result
    
    # Use nose or neck as head reference
    addr_head = _get_joint(addr, MHR_NOSE)
    top_head = _get_joint(top, MHR_NOSE)
    fin_head = _get_joint(finish, MHR_NOSE)
    
    if addr_head is None:
        addr_head = _get_joint(addr, MHR_NECK)
    if top_head is None:
        top_head = _get_joint(top, MHR_NECK)
    if fin_head is None:
        fin_head = _get_joint(finish, MHR_NECK)
    
    if any(h is None for h in [addr_head, top_head, fin_head]):
        return result
    
    # Estimate scale
    scale = _estimate_scale(addr)
    
    # Vertical rise from top to finish
    # SAM-3D uses Y-down, so smaller Y = higher
    # Rise = top_y - fin_y (positive if head rose)
    rise = (top_head[1] - fin_head[1]) * scale
    result["head_rise_top_to_finish_cm"] = round(rise, 2)
    
    # Lateral shift from address to finish (X axis)
    lateral = (fin_head[0] - addr_head[0]) * scale
    result["head_lateral_shift_address_to_finish_cm"] = round(lateral, 2)
    
    return result


def compute_hand_finish_position(
    phase_joints: PhaseJoints,
    handedness: str = "right"
) -> Dict[str, Any]:
    """
    Compute hand position at finish relative to body.
    
    Returns:
        - hand_height_finish_norm: Height relative to neck/torso
        - hand_depth_finish_norm: Depth relative to chest plane
        - hand_height_finish_label: "low" | "neutral" | "high"
        - hand_depth_finish_label: "shallow" | "neutral" | "deep"
    """
    result: Dict[str, Any] = {
        "hand_height_finish_norm": None,
        "hand_depth_finish_norm": None,
        "hand_height_finish_label": None,
        "hand_depth_finish_label": None,
    }
    
    finish = phase_joints.get("finish")
    if finish is None:
        return result
    
    # Get lead wrist (left for right-handed)
    if handedness.lower() == "right":
        wrist = _get_joint(finish, MHR_L_WRIST)
    else:
        wrist = _get_joint(finish, 41)  # MHR_R_WRIST
    
    neck = _get_joint(finish, MHR_NECK)
    l_sh = _get_joint(finish, MHR_L_SHOULDER)
    r_sh = _get_joint(finish, MHR_R_SHOULDER)
    l_hip = _get_joint(finish, MHR_L_HIP)
    
    if any(j is None for j in [wrist, neck, l_sh, r_sh]):
        return result
    
    # Height: wrist Y relative to neck Y (normalized by torso length)
    torso_scale = 1.0
    if l_hip is not None:
        torso_len = abs(neck[1] - l_hip[1])
        if torso_len > 0.01:
            torso_scale = torso_len
    
    # Y-down: wrist above neck = smaller Y value
    height_diff = neck[1] - wrist[1]  # Positive when wrist above neck
    height_norm = height_diff / torso_scale if torso_scale > 0.01 else 0.0
    result["hand_height_finish_norm"] = round(height_norm, 3)
    
    # Height label thresholds
    if height_norm > 0.3:
        result["hand_height_finish_label"] = "high"
    elif height_norm < -0.1:
        result["hand_height_finish_label"] = "low"
    else:
        result["hand_height_finish_label"] = "neutral"
    
    # Depth: distance along chest-facing direction
    # Chest normal = cross(shoulder_line, up)
    shoulder_vec = r_sh - l_sh
    up = np.array([0, -1, 0])
    chest_normal = np.cross(shoulder_vec, up)
    chest_normal_len = np.linalg.norm(chest_normal)
    
    if chest_normal_len > 0.01:
        chest_normal = chest_normal / chest_normal_len
        
        # Vector from chest center to wrist
        chest_center = _midpoint(l_sh, r_sh)
        wrist_offset = wrist - chest_center
        
        # Project onto chest normal (positive = in front)
        depth = np.dot(wrist_offset, chest_normal)
        
        # Normalize by shoulder width
        shoulder_width = np.linalg.norm(shoulder_vec)
        depth_norm = depth / shoulder_width if shoulder_width > 0.01 else 0.0
        result["hand_depth_finish_norm"] = round(depth_norm, 3)
        
        # Depth label thresholds
        if depth_norm > 0.5:
            result["hand_depth_finish_label"] = "deep"
        elif depth_norm < -0.2:
            result["hand_depth_finish_label"] = "shallow"
        else:
            result["hand_depth_finish_label"] = "neutral"
    
    return result


def compute_finish_metrics(
    phase_joints: PhaseJoints,
    handedness: str = "right"
) -> Dict[str, Any]:
    """
    Compute all finish-related metrics.
    
    Args:
        phase_joints: Dict with 'address', 'top', 'impact', 'finish' keys,
                     each containing (70, 3) MHR joints array.
        handedness: "right" or "left"
    
    Returns:
        Flat dict with all finish metrics, ready for serialization.
    """
    metrics: Dict[str, Any] = {}
    
    # Convert lists to numpy arrays if needed
    converted: PhaseJoints = {}
    for phase in ["address", "top", "impact", "finish"]:
        data = phase_joints.get(phase)
        if data is not None:
            if isinstance(data, dict) and "joints3d" in data:
                joints = data["joints3d"]
            else:
                joints = data
            
            if joints is not None and not isinstance(joints, np.ndarray):
                joints = np.array(joints)
            converted[phase] = joints
        else:
            converted[phase] = None
    
    # Compute individual metrics
    balance = compute_finish_balance(converted)
    if balance is not None:
        metrics["finish_balance"] = round(balance, 3)
    
    spine = compute_finish_spine_extension(converted)
    metrics.update(spine)
    
    rotation = compute_finish_rotation(converted)
    metrics.update(rotation)
    
    head = compute_head_recovery(converted)
    metrics.update(head)
    
    hand = compute_hand_finish_position(converted, handedness)
    metrics.update(hand)
    
    return metrics

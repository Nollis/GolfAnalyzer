"""
MHR Sway Metrics - Track pelvis and shoulder lateral movement through swing.

Uses MHR-70 3D joint positions to compute displacement from address
at each swing phase (top, impact, finish).
"""

import numpy as np
from typing import Dict, Any, Optional, TypedDict


class PhaseJoints(TypedDict):
    """MHR-70 joints for each swing phase."""
    address: np.ndarray  # (70, 3)
    top: np.ndarray      # (70, 3)
    impact: np.ndarray   # (70, 3)
    finish: np.ndarray   # (70, 3)


# MHR-70 Joint Indices
MHR_L_SHOULDER = 5
MHR_R_SHOULDER = 6
MHR_L_HIP = 9
MHR_R_HIP = 10


def _get_joint(joints: np.ndarray, idx: int) -> Optional[np.ndarray]:
    """Get joint position as (x, y, z) array."""
    if joints is None or idx >= len(joints):
        return None
    return joints[idx]


def _midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Get midpoint between two 3D points."""
    return (p1 + p2) / 2


def _estimate_scale(joints: np.ndarray) -> float:
    """
    Estimate body scale from torso length.
    Returns scale factor to convert to centimeters (approx).
    """
    lh = _get_joint(joints, MHR_L_HIP)
    ls = _get_joint(joints, MHR_L_SHOULDER)
    if lh is None or ls is None:
        return 100.0
    torso_len = np.linalg.norm(ls - lh)
    if torso_len > 0.01:
        return 50.0 / torso_len
    return 100.0


def _compute_center_displacement_xz(
    ref_joints: np.ndarray,
    target_joints: np.ndarray,
    left_idx: int,
    right_idx: int,
    scale: float
) -> Optional[float]:
    """
    Compute XZ plane displacement of body segment center between phases.
    
    Returns displacement in cm (estimated).
    """
    ref_l = _get_joint(ref_joints, left_idx)
    ref_r = _get_joint(ref_joints, right_idx)
    tgt_l = _get_joint(target_joints, left_idx)
    tgt_r = _get_joint(target_joints, right_idx)
    
    if any(j is None for j in [ref_l, ref_r, tgt_l, tgt_r]):
        return None
    
    ref_center = _midpoint(ref_l, ref_r)
    tgt_center = _midpoint(tgt_l, tgt_r)
    
    # XZ displacement only (horizontal plane)
    dx = tgt_center[0] - ref_center[0]
    dz = tgt_center[2] - ref_center[2]
    
    displacement = np.sqrt(dx**2 + dz**2) * scale
    
    return float(displacement)


def _compute_lateral_sway(
    ref_joints: np.ndarray,
    target_joints: np.ndarray,
    left_idx: int,
    right_idx: int,
    scale: float
) -> Optional[float]:
    """
    Compute lateral (X-axis) sway of body segment center.
    
    Positive = toward lead side (left for right-handed).
    Returns in cm (estimated).
    """
    ref_l = _get_joint(ref_joints, left_idx)
    ref_r = _get_joint(ref_joints, right_idx)
    tgt_l = _get_joint(target_joints, left_idx)
    tgt_r = _get_joint(target_joints, right_idx)
    
    if any(j is None for j in [ref_l, ref_r, tgt_l, tgt_r]):
        return None
    
    ref_center = _midpoint(ref_l, ref_r)
    tgt_center = _midpoint(tgt_l, tgt_r)
    
    # X displacement (lateral)
    dx = (tgt_center[0] - ref_center[0]) * scale
    
    return float(dx)


def compute_sway_from_address(phase_joints: PhaseJoints) -> Dict[str, Optional[float]]:
    """
    Compute pelvis and shoulder sway from address through all phases.
    
    Sway is measured as lateral (X-axis) displacement in the horizontal plane.
    Positive values indicate movement toward lead side (left for right-handed).
    
    Args:
        phase_joints: Dict with 'address', 'top', 'impact', 'finish' keys,
                     each containing (70, 3) MHR joints array.
    
    Returns:
        Dict with sway values in cm for each phase:
        - pelvis_sway_top_cm, pelvis_sway_impact_cm, pelvis_sway_finish_cm
        - shoulder_sway_top_cm, shoulder_sway_impact_cm, shoulder_sway_finish_cm
    """
    result: Dict[str, Optional[float]] = {
        "pelvis_sway_top_cm": None,
        "pelvis_sway_impact_cm": None,
        "pelvis_sway_finish_cm": None,
        "shoulder_sway_top_cm": None,
        "shoulder_sway_impact_cm": None,
        "shoulder_sway_finish_cm": None,
    }
    
    # Convert to numpy if needed
    def to_np(data):
        if data is None:
            return None
        if isinstance(data, dict) and "joints3d" in data:
            data = data["joints3d"]
        if data is not None and not isinstance(data, np.ndarray):
            data = np.array(data)
        return data
    
    addr = to_np(phase_joints.get("address"))
    top = to_np(phase_joints.get("top"))
    impact = to_np(phase_joints.get("impact"))
    finish = to_np(phase_joints.get("finish"))
    
    if addr is None:
        return result
    
    # Estimate scale from address pose
    scale = _estimate_scale(addr)
    
    phases = {
        "top": top,
        "impact": impact,
        "finish": finish,
    }
    
    for phase_name, joints in phases.items():
        if joints is None:
            continue
        
        # Pelvis sway (using hips)
        pelvis_sway = _compute_lateral_sway(
            addr, joints, MHR_L_HIP, MHR_R_HIP, scale
        )
        if pelvis_sway is not None:
            result[f"pelvis_sway_{phase_name}_cm"] = round(pelvis_sway, 2)
        
        # Shoulder sway
        shoulder_sway = _compute_lateral_sway(
            addr, joints, MHR_L_SHOULDER, MHR_R_SHOULDER, scale
        )
        if shoulder_sway is not None:
            result[f"shoulder_sway_{phase_name}_cm"] = round(shoulder_sway, 2)
    
    return result


def compute_sway_range(phase_joints: PhaseJoints) -> Dict[str, Optional[float]]:
    """
    Compute the total range of sway through the swing.
    
    Returns:
        - pelvis_sway_range_cm: Max - min pelvis X position through swing
        - shoulder_sway_range_cm: Max - min shoulder X position through swing
    """
    result: Dict[str, Optional[float]] = {
        "pelvis_sway_range_cm": None,
        "shoulder_sway_range_cm": None,
    }
    
    def to_np(data):
        if data is None:
            return None
        if isinstance(data, dict) and "joints3d" in data:
            data = data["joints3d"]
        if data is not None and not isinstance(data, np.ndarray):
            data = np.array(data)
        return data
    
    addr = to_np(phase_joints.get("address"))
    if addr is None:
        return result
    
    scale = _estimate_scale(addr)
    
    # Collect all phases
    phases = [
        to_np(phase_joints.get("address")),
        to_np(phase_joints.get("top")),
        to_np(phase_joints.get("impact")),
        to_np(phase_joints.get("finish")),
    ]
    
    pelvis_x_positions = []
    shoulder_x_positions = []
    
    for joints in phases:
        if joints is None:
            continue
        
        l_hip = _get_joint(joints, MHR_L_HIP)
        r_hip = _get_joint(joints, MHR_R_HIP)
        if l_hip is not None and r_hip is not None:
            pelvis_x = (l_hip[0] + r_hip[0]) / 2
            pelvis_x_positions.append(pelvis_x)
        
        l_sh = _get_joint(joints, MHR_L_SHOULDER)
        r_sh = _get_joint(joints, MHR_R_SHOULDER)
        if l_sh is not None and r_sh is not None:
            shoulder_x = (l_sh[0] + r_sh[0]) / 2
            shoulder_x_positions.append(shoulder_x)
    
    if len(pelvis_x_positions) >= 2:
        pelvis_range = (max(pelvis_x_positions) - min(pelvis_x_positions)) * scale
        result["pelvis_sway_range_cm"] = round(pelvis_range, 2)
    
    if len(shoulder_x_positions) >= 2:
        shoulder_range = (max(shoulder_x_positions) - min(shoulder_x_positions)) * scale
        result["shoulder_sway_range_cm"] = round(shoulder_range, 2)
    
    return result


def compute_all_sway_metrics(phase_joints: PhaseJoints) -> Dict[str, Any]:
    """
    Compute all sway-related metrics.
    
    Returns:
        Flat dict with all sway metrics.
    """
    metrics: Dict[str, Any] = {}
    
    sway = compute_sway_from_address(phase_joints)
    metrics.update(sway)
    
    sway_range = compute_sway_range(phase_joints)
    metrics.update(sway_range)
    
    return metrics

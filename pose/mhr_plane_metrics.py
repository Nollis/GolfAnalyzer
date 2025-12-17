"""
MHR Swing Plane Metrics - Estimate swing plane from body pose without club.

Uses spine vector and lead arm vector to define a reference swing plane,
then measures deviation at top and impact positions.
"""

import math
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
MHR_L_WRIST = 62
MHR_R_WRIST = 41
MHR_NECK = 69


def _get_joint(joints: np.ndarray, idx: int) -> Optional[np.ndarray]:
    """Get joint position as (x, y, z) array."""
    if joints is None or idx >= len(joints):
        return None
    return joints[idx]


def _midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Get midpoint between two 3D points."""
    return (p1 + p2) / 2


def _normalize(v: np.ndarray) -> np.ndarray:
    """Normalize a vector, returning zero vector if too small."""
    norm = np.linalg.norm(v)
    if norm < 1e-6:
        return np.zeros(3)
    return v / norm


def _angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate angle between two 3D vectors in degrees."""
    v1_norm = np.linalg.norm(v1)
    v2_norm = np.linalg.norm(v2)
    if v1_norm < 1e-6 or v2_norm < 1e-6:
        return 0.0
    cos_angle = np.clip(np.dot(v1, v2) / (v1_norm * v2_norm), -1.0, 1.0)
    return math.degrees(math.acos(cos_angle))


def _angle_between_planes(n1: np.ndarray, n2: np.ndarray) -> float:
    """
    Calculate angle between two planes defined by their normals.
    
    Returns angle in degrees (0-90 range).
    """
    n1_normalized = _normalize(n1)
    n2_normalized = _normalize(n2)
    
    if np.linalg.norm(n1_normalized) < 0.5 or np.linalg.norm(n2_normalized) < 0.5:
        return 0.0
    
    cos_angle = np.abs(np.dot(n1_normalized, n2_normalized))
    cos_angle = np.clip(cos_angle, 0.0, 1.0)
    return math.degrees(math.acos(cos_angle))


def _compute_spine_vector(joints: np.ndarray) -> Optional[np.ndarray]:
    """
    Compute spine vector from pelvis center to neck.
    
    Returns normalized vector pointing up the spine.
    """
    l_hip = _get_joint(joints, MHR_L_HIP)
    r_hip = _get_joint(joints, MHR_R_HIP)
    neck = _get_joint(joints, MHR_NECK)
    
    if any(j is None for j in [l_hip, r_hip]):
        return None
    
    pelvis = _midpoint(l_hip, r_hip)
    
    if neck is None:
        # Fallback to shoulder midpoint
        l_sh = _get_joint(joints, MHR_L_SHOULDER)
        r_sh = _get_joint(joints, MHR_R_SHOULDER)
        if l_sh is None or r_sh is None:
            return None
        upper = _midpoint(l_sh, r_sh)
    else:
        upper = neck
    
    spine = upper - pelvis
    return _normalize(spine)


def _compute_lead_arm_vector(
    joints: np.ndarray,
    handedness: str = "right"
) -> Optional[np.ndarray]:
    """
    Compute lead arm vector from shoulder to wrist.
    
    For right-handed: left arm (shoulder to wrist).
    Returns normalized vector.
    """
    if handedness.lower() == "right":
        shoulder = _get_joint(joints, MHR_L_SHOULDER)
        wrist = _get_joint(joints, MHR_L_WRIST)
    else:
        shoulder = _get_joint(joints, MHR_R_SHOULDER)
        wrist = _get_joint(joints, MHR_R_WRIST)
    
    if shoulder is None or wrist is None:
        return None
    
    arm = wrist - shoulder
    return _normalize(arm)


def _compute_swing_plane_normal(
    joints: np.ndarray,
    handedness: str = "right"
) -> Optional[np.ndarray]:
    """
    Compute swing plane normal from spine and lead arm vectors.
    
    The swing plane is defined by the cross product of:
    - Spine vector (pelvis → neck)
    - Lead arm vector (shoulder → wrist)
    
    Returns normalized plane normal vector.
    """
    spine = _compute_spine_vector(joints)
    arm = _compute_lead_arm_vector(joints, handedness)
    
    if spine is None or arm is None:
        return None
    
    # Plane normal = cross(spine, arm)
    # This gives a vector perpendicular to both spine and arm
    normal = np.cross(spine, arm)
    
    return _normalize(normal)


def _compute_ideal_plane_normal(
    addr_joints: np.ndarray,
    handedness: str = "right"
) -> Optional[np.ndarray]:
    """
    Compute an "ideal" swing plane normal based on address position.
    
    The ideal plane is simply the arm/spine plane at address, which
    represents the setup plane the golfer established.
    
    A good swing returns to near this original plane at impact.
    
    Returns normalized plane normal.
    """
    # Use the actual arm/spine plane at address as the ideal reference
    return _compute_swing_plane_normal(addr_joints, handedness)


def compute_swing_plane_at_phase(
    joints: np.ndarray,
    addr_joints: np.ndarray,
    handedness: str = "right",
    ideal_angle_deg: float = 50.0
) -> Dict[str, Optional[float]]:
    """
    Compute swing plane deviation at a specific phase.
    
    Returns:
        - arm_plane_angle_deg: Angle of current arm/spine plane from horizontal
        - deviation_from_ideal_deg: How far the current plane is from ideal
    """
    result = {
        "arm_plane_angle_deg": None,
        "deviation_from_ideal_deg": None,
    }
    
    # Compute current swing plane normal
    current_normal = _compute_swing_plane_normal(joints, handedness)
    if current_normal is None:
        return result
    
    # Compute angle of current plane from horizontal
    # The plane angle is 90° - angle_between(normal, up)
    up = np.array([0, -1, 0])
    normal_to_up_angle = _angle_between_vectors(current_normal, up)
    # Plane angle is complement
    plane_angle = 90.0 - abs(90.0 - normal_to_up_angle)
    result["arm_plane_angle_deg"] = round(plane_angle, 2)
    
    # Compute ideal plane normal based on address position
    ideal_normal = _compute_ideal_plane_normal(addr_joints, handedness)
    if ideal_normal is not None:
        deviation = _angle_between_planes(current_normal, ideal_normal)
        result["deviation_from_ideal_deg"] = round(deviation, 2)
    
    return result


def compute_swing_plane_metrics(
    phase_joints: PhaseJoints,
    handedness: str = "right"
) -> Dict[str, Any]:
    """
    Compute swing plane metrics at TOP and IMPACT.
    
    The swing plane is estimated from the spine and lead arm vectors.
    We measure:
    1. Plane angle at each phase
    2. Deviation from an "ideal" reference plane
    3. How much the plane shifted from top to impact
    
    Args:
        phase_joints: Dict with 'address', 'top', 'impact', 'finish' keys.
        handedness: "right" or "left"
    
    Returns:
        Dict with swing plane metrics.
    """
    result: Dict[str, Any] = {
        "swing_plane_top_deg": None,
        "swing_plane_impact_deg": None,
        "swing_plane_deviation_top_deg": None,
        "swing_plane_deviation_impact_deg": None,
        "swing_plane_shift_top_to_impact_deg": None,
        "arm_above_plane_at_top": None,
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
    
    if addr is None:
        return result
    
    # Compute at TOP
    if top is not None:
        top_metrics = compute_swing_plane_at_phase(top, addr, handedness)
        if top_metrics.get("arm_plane_angle_deg") is not None:
            result["swing_plane_top_deg"] = top_metrics["arm_plane_angle_deg"]
        if top_metrics.get("deviation_from_ideal_deg") is not None:
            result["swing_plane_deviation_top_deg"] = top_metrics["deviation_from_ideal_deg"]
        
        # Check if arm is above ideal plane
        # If deviation is positive and plane angle > ideal, arm is above
        ideal_angle = 50.0
        if result["swing_plane_top_deg"] is not None:
            result["arm_above_plane_at_top"] = result["swing_plane_top_deg"] > (ideal_angle + 5)
    
    # Compute at IMPACT
    if impact is not None:
        impact_metrics = compute_swing_plane_at_phase(impact, addr, handedness)
        if impact_metrics.get("arm_plane_angle_deg") is not None:
            result["swing_plane_impact_deg"] = impact_metrics["arm_plane_angle_deg"]
        if impact_metrics.get("deviation_from_ideal_deg") is not None:
            result["swing_plane_deviation_impact_deg"] = impact_metrics["deviation_from_ideal_deg"]
    
    # Compute plane shift from top to impact
    if result["swing_plane_top_deg"] is not None and result["swing_plane_impact_deg"] is not None:
        shift = result["swing_plane_impact_deg"] - result["swing_plane_top_deg"]
        result["swing_plane_shift_top_to_impact_deg"] = round(shift, 2)
    
    return result

import json
from pathlib import Path
from typing import List, Optional
import numpy as np

ADDRESS_POSE: Optional[List[List[List[float]]]] = None

def load_address_pose(path: str | Path = "pose/presets/address_pose.json") -> None:
    """
    Load the address_pose.json file into ADDRESS_POSE (24 x 3 x 3 list of floats).
    Safe to call multiple times.
    """
    global ADDRESS_POSE
    p = Path(path)
    if not p.exists():
        # Try absolute path relative to project root if relative path fails
        root = Path(__file__).parent.parent.parent
        p = root / path
        
    if not p.exists():
        print(f"[WARN] address_pose.json not found at {p}")
        ADDRESS_POSE = None
        return

    try:
        data = json.loads(p.read_text())
        pose = data.get("smpl_pose")
        if not isinstance(pose, list) or len(pose) < 24:
            print(f"[WARN] address_pose.json has unexpected format")
            ADDRESS_POSE = None
            return

        ADDRESS_POSE = pose
        print("[INFO] Loaded address_pose.json with", len(ADDRESS_POSE), "joints")
    except Exception as e:
        print(f"[ERROR] Failed to load address_pose.json: {e}")
        ADDRESS_POSE = None


def mat3_to_quat(m: list[list[float]]) -> np.ndarray:
    """
    Convert 3x3 rotation matrix (row-major) to a unit quaternion [x, y, z, w].
    Pure numpy implementation.
    """
    R = np.array(m, dtype=np.float64)
    t = np.trace(R)
    if t > 0.0:
        s = np.sqrt(t + 1.0) * 2.0
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    else:
        # Find the largest diagonal element and proceed accordingly
        if R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s

    q = np.array([x, y, z, w], dtype=np.float64)
    q_norm = np.linalg.norm(q)
    if q_norm > 0:
        q /= q_norm
    return q


def quat_to_mat3(q: np.ndarray) -> list[list[float]]:
    """
    Convert quaternion [x, y, z, w] back to 3x3 rotation matrix.
    """
    x, y, z, w = q
    xx = x * x; yy = y * y; zz = z * z
    xy = x * y; xz = x * z; yz = y * z
    wx = w * x; wy = w * y; wz = w * z

    m = np.empty((3, 3), dtype=np.float64)
    m[0, 0] = 1.0 - 2.0 * (yy + zz)
    m[0, 1] = 2.0 * (xy - wz)
    m[0, 2] = 2.0 * (xz + wy)

    m[1, 0] = 2.0 * (xy + wz)
    m[1, 1] = 1.0 - 2.0 * (xx + zz)
    m[1, 2] = 2.0 * (yz - wx)

    m[2, 0] = 2.0 * (xz - wy)
    m[2, 1] = 2.0 * (yz + wx)
    m[2, 2] = 1.0 - 2.0 * (xx + yy)

    return m.tolist()


def slerp(q0: np.ndarray, q1: np.ndarray, alpha: float) -> np.ndarray:
    """
    Spherical linear interpolation between q0 and q1.
    alpha in [0,1].
    """
    # Normalize
    q0 = q0 / np.linalg.norm(q0)
    q1 = q1 / np.linalg.norm(q1)

    dot = np.dot(q0, q1)

    # Ensure shortest path
    if dot < 0.0:
        q1 = -q1
        dot = -dot

    dot = np.clip(dot, -1.0, 1.0)

    if dot > 0.9995:
        # Linear fall-back for very small angles
        q = q0 + alpha * (q1 - q0)
        return q / np.linalg.norm(q)

    theta_0 = np.arccos(dot)
    sin_theta_0 = np.sin(theta_0)
    theta = theta_0 * alpha
    sin_theta = np.sin(theta)

    s0 = np.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0

    return (s0 * q0) + (s1 * q1)


TORSO_JOINTS = {3, 6, 9, 12}  # spine1, spine2, spine3, neck (by index) - EXCLUDING pelvis (0) to keep global rot
LOWER_BODY = {1, 2, 4, 5, 7, 8}  # hips, knees, ankles


def blend_with_address(
    dtl_pose: list[list[list[float]]],
    strength_torso: float = 0.45,
    strength_lower: float = 0.25,
) -> list[list[list[float]]]:
    """
    Blend the incoming DTL SMPL pose (24 x 3 x 3) with ADDRESS_POSE.
    Alpha is stronger for torso, weaker for legs, zero for arms/hands.
    """
    if ADDRESS_POSE is None:
        return dtl_pose

    if len(dtl_pose) != len(ADDRESS_POSE):
        # Fallback if dimensions differ
        return dtl_pose

    out: list[list[list[float]]] = []

    for idx, (A, B) in enumerate(zip(ADDRESS_POSE, dtl_pose)):
        if idx in TORSO_JOINTS:
            alpha = strength_torso
        elif idx in LOWER_BODY:
            alpha = strength_lower
        else:
            alpha = 0.0

        if alpha <= 0.0:
            out.append(B)
            continue

        qA = mat3_to_quat(A)
        qB = mat3_to_quat(B)
        q  = slerp(qA, qB, alpha)
        out.append(quat_to_mat3(q))

    return out

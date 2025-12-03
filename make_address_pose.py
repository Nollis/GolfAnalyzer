import json
import math
from pathlib import Path

# --- 1. SMPL joint order (your backend names) --------------------
SMPL_JOINT_ORDER = [
    "pelvis",      # 0
    "l_hip",       # 1
    "r_hip",       # 2
    "spine1",      # 3
    "l_knee",      # 4
    "r_knee",      # 5
    "spine2",      # 6
    "l_ankle",     # 7
    "r_ankle",     # 8
    "spine3",      # 9
    "l_foot",      # 10 (no bot bone – ignored)
    "r_foot",      # 11 (no bot bone – ignored)
    "neck",        # 12
    "l_collar",    # 13 (no bot bone – ignored)
    "r_collar",    # 14 (no bot bone – ignored)
    "head",        # 15
    "l_shoulder",  # 16
    "r_shoulder",  # 17
    "l_elbow",     # 18
    "r_elbow",     # 19
    "l_wrist",     # 20
    "r_wrist",     # 21
    "l_hand",      # 22 (no bot bone – ignored)
    "r_hand",      # 23 (no bot bone – ignored)
]


# --- 2. Basic math helpers ---------------------------------------
def matmul(a, b):
    """3x3 * 3x3 matrix multiply."""
    return [
        [
            sum(a[i][k] * b[k][j] for k in range(3))
            for j in range(3)
        ]
        for i in range(3)
    ]


def euler_xyz_to_mat3(rx_deg: float, ry_deg: float, rz_deg: float):
    """
    Build a 3x3 rotation matrix from XYZ Euler angles (degrees),
    matching the 'XYZ' convention you use in Three/Blender.
    Order: R = Rz * Ry * Rx.
    """
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)

    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)

    Rx = [
        [1, 0, 0],
        [0, cx, -sx],
        [0, sx, cx],
    ]
    Ry = [
        [cy, 0, sy],
        [0, 1, 0],
        [-sy, 0, cy],
    ]
    Rz = [
        [cz, -sz, 0],
        [sz, cz, 0],
        [0, 0, 1],
    ]

    R = matmul(Rz, matmul(Ry, Rx))
    # nice rounding for JSON
    return [[round(v, 8) for v in row] for row in R]


def ident():
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]


# --- 3. Define an "address" pose in degrees -----------------------
# These are *local* joint rotations relative to SMPL rest:
#   - pelvis & spine: forward bend
#   - hips/knees/ankles: athletic posture
#   - everything else = identity (your DTL pose will override arms etc.)
ANGLE_CONFIG = {
    "pelvis":   (-20.0, 0.0, 0.0),

    "spine1":   (-10.0, 0.0, 0.0),
    "spine2":   ( -5.0, 0.0, 0.0),
    "spine3":   ( -5.0, 0.0, 0.0),

    # Wider stance: Abduct hips (rotate around Z axis)
    # Left hip: +Z moves leg out (left)
    # Right hip: -Z moves leg out (right)
    "l_hip":    (-15.0, 0.0, 10.0),
    "r_hip":    (-15.0, 0.0, -10.0),

    "l_knee":   ( 25.0, 0.0, 0.0),
    "r_knee":   ( 25.0, 0.0, 0.0),

    "l_ankle":  (-10.0, 0.0, 0.0),
    "r_ankle":  (-10.0, 0.0, 0.0),

    # Closer hands: Adduct shoulders/arms
    # Left shoulder: -Z moves arm in (right)
    # Right shoulder: +Z moves arm in (left)
    # Also slight internal rotation (Y) to face palms inward
    "l_shoulder": (0.0, 0.0, -15.0),
    "r_shoulder": (0.0, 0.0, 15.0),
    
    # Adjust elbows to straighten arms slightly if needed, or keep identity
    "l_elbow":    (0.0, 0.0, 0.0),
    "r_elbow":    (0.0, 0.0, 0.0),
}


def build_address_pose():
    mats = []
    for name in SMPL_JOINT_ORDER:
        if name in ANGLE_CONFIG:
            rx, ry, rz = ANGLE_CONFIG[name]
            m = euler_xyz_to_mat3(rx, ry, rz)
        else:
            m = ident()
        mats.append(m)
    return mats


# --- 4. Write JSON file ------------------------------------------
def main(outfile: str = "address_pose.json"):
    pose_mats = build_address_pose()
    data = {"smpl_pose": pose_mats}

    Path(outfile).write_text(json.dumps(data, indent=2))
    print(f"Wrote {outfile} with {len(pose_mats)} joints.")


if __name__ == "__main__":
    main()


import numpy as np
from typing import List, Optional, Tuple

# SMPL Kinematic Tree (Parent indices)
# -1 means root (no parent)
SMPL_PARENTS = [
    -1, # 0: Pelvis
    0,  # 1: L_Hip
    0,  # 2: R_Hip
    0,  # 3: Spine1
    1,  # 4: L_Knee
    2,  # 5: R_Knee
    3,  # 6: Spine2
    4,  # 7: L_Ankle
    5,  # 8: R_Ankle
    6,  # 9: Spine3
    7,  # 10: L_Foot
    8,  # 11: R_Foot
    9,  # 12: Neck
    9,  # 13: L_Collar
    9,  # 14: R_Collar
    12, # 15: Head
    13, # 16: L_Shoulder
    14, # 17: R_Shoulder
    16, # 18: L_Elbow
    17, # 19: R_Elbow
    18, # 20: L_Wrist
    19, # 21: R_Wrist
    20, # 22: L_Hand
    21, # 23: R_Hand
]

# Standard SMPL Rest Pose Offsets (Approximate Mean Shape)
# These are relative to parent. Units: meters (approx)
# Extracted from a mean SMPL model
SMPL_MEAN_OFFSETS = np.array([
    [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00], # 0: Pelvis (Root)
    [ 0.05858135, -0.07724548, -0.02579638], # 1: L_Hip
    [-0.06030973, -0.07477074, -0.02694701], # 2: R_Hip
    [ 0.00443945,  0.12440352, -0.03838522], # 3: Spine1
    [ 0.04325663, -0.38368791, -0.00846453], # 4: L_Knee
    [-0.0426604,  -0.38617337, -0.01296848], # 5: R_Knee
    [ 0.00448844,  0.1379564,  -0.02682033], # 6: Spine2
    [ 0.01905555, -0.4200455,  -0.03456167], # 7: L_Ankle
    [-0.02012772, -0.4261662,  -0.03744791], # 8: R_Ankle
    [ 0.00226458,  0.05603239,  0.00285505], # 9: Spine3
    [ 0.04105436, -0.06604639,  0.14035748], # 10: L_Foot
    [-0.04011405, -0.06732602,  0.13564927], # 11: R_Foot
    [-0.00292163,  0.21242046,  0.03370688], # 12: Neck
    [ 0.07179865,  0.11399969, -0.01889817], # 13: L_Collar
    [-0.07114712,  0.11404169, -0.01819855], # 14: R_Collar
    [ 0.00035071,  0.07062404,  0.02261177], # 15: Head
    [ 0.11954173, -0.02285875, -0.00653049], # 16: L_Shoulder
    [-0.11605282, -0.0236341,  -0.00628341], # 17: R_Shoulder
    [ 0.26648735, -0.01674588, -0.03275451], # 18: L_Elbow
    [-0.27105814, -0.01713843, -0.03052622], # 19: R_Elbow
    [ 0.25072098, -0.01396867, -0.01506389], # 20: L_Wrist
    [-0.25310679, -0.01336094, -0.01556372], # 21: R_Wrist
    [ 0.08444394, -0.0104775,  -0.01291665], # 22: L_Hand
    [-0.08830745, -0.01666065, -0.01029846], # 23: R_Hand
])

def forward_kinematics(
    rotations: List[List[List[float]]], 
    root_position: List[float] = [0.0, 0.0, 0.0],
    offsets: Optional[np.ndarray] = None
) -> List[List[float]]:
    """
    Compute global joint positions from local rotations and offsets.
    
    Args:
        rotations: 24x3x3 rotation matrices (local relative to parent)
        root_position: Global position of the root joint (Pelvis)
        offsets: 24x3 bone offsets (relative to parent). If None, uses SMPL_MEAN_OFFSETS.
    
    Returns:
        List of 24 [x, y, z] global joint positions.
    """
    if offsets is None:
        offsets = SMPL_MEAN_OFFSETS
        
    # Convert inputs to numpy
    rots = np.array(rotations) # (24, 3, 3)
    root_pos = np.array(root_position)
    
    # Global transforms (orientation and position)
    # global_rots[i] = global_rots[parent] @ local_rots[i]
    # global_pos[i] = global_pos[parent] + global_rots[parent] @ local_offset[i]
    
    global_rots = np.zeros((24, 3, 3))
    global_pos = np.zeros((24, 3))
    
    # Root (0)
    global_rots[0] = rots[0]
    global_pos[0] = root_pos
    
    for i in range(1, 24):
        parent = SMPL_PARENTS[i]
        
        # Global rotation
        global_rots[i] = global_rots[parent] @ rots[i]
        
        # Global position
        # Offset is in parent's frame? No, usually offsets are in rest pose frame.
        # In SMPL: J_i = J_parent + R_parent_global * Offset_i_rest
        # Wait, SMPL offsets are defined in the T-pose frame.
        # So yes, we rotate the offset by the parent's global rotation.
        
        offset_rotated = global_rots[parent] @ offsets[i]
        global_pos[i] = global_pos[parent] + offset_rotated
        
    return global_pos.tolist()

def estimate_skeleton_offsets(joints_3d: List[List[float]]) -> np.ndarray:
    """
    Estimate bone offsets from a posed 3D skeleton.
    Note: This is an approximation because we don't know the rotations that generated this pose.
    However, for simple scaling, we can just compute the lengths and apply them to the mean direction.
    """
    joints = np.array(joints_3d)
    offsets = np.zeros((24, 3))
    
    # Use mean offsets as base for direction
    mean_offsets = SMPL_MEAN_OFFSETS.copy()
    
    for i in range(1, 24):
        parent = SMPL_PARENTS[i]
        
        # Actual bone vector in current pose
        bone_vec = joints[i] - joints[parent]
        bone_len = np.linalg.norm(bone_vec)
        
        # Mean bone vector
        mean_vec = mean_offsets[i]
        mean_len = np.linalg.norm(mean_vec)
        
        if mean_len > 1e-6:
            # Scale mean offset to match actual length
            scale = bone_len / mean_len
            offsets[i] = mean_vec * scale
        else:
            offsets[i] = mean_vec
            
    return offsets

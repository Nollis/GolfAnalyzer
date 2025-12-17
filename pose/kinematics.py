import numpy as np
from typing import List, Tuple

# SMPL kinematic tree (parent indices)
# -1 means root
SMPL_PARENTS = [
    -1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19, 20, 21
]

def calculate_offsets_from_pose(
    joints_3d: List[List[float]], 
    rotations: List[List[List[float]]]
) -> np.ndarray:
    """
    Calculate bone offsets from a given pose (joints and rotations).
    This ensures we capture the subject's specific bone lengths.
    
    Args:
        joints_3d: (24, 3) joint positions
        rotations: (24, 3, 3) rotation matrices (global or local? HybrIK usually gives global relative to camera or root?)
                   Wait, HybrIK smpl_pose is usually relative rotations (pose parameters).
                   Let's assume standard SMPL relative rotations.
                   
    Returns:
        offsets: (24, 3) bone vectors relative to parent
    """
    joints = np.array(joints_3d)
    rots = np.array(rotations)
    offsets = np.zeros((24, 3))
    
    # We need Global Rotations to invert the relationship:
    # Global_Pos_Child = Global_Pos_Parent + Global_Rot_Parent @ Offset_Child
    # => Offset_Child = inv(Global_Rot_Parent) @ (Global_Pos_Child - Global_Pos_Parent)
    
    # First, compute global rotations from relative ones
    global_rots = np.zeros((24, 3, 3))
    global_rots[0] = rots[0]
    
    for i in range(1, 24):
        parent = SMPL_PARENTS[i]
        global_rots[i] = global_rots[parent] @ rots[i]
        
    # Now compute offsets
    # Root offset is just 0 (or root position, but we handle root pos separately)
    offsets[0] = np.zeros(3) 
    
    for i in range(1, 24):
        parent = SMPL_PARENTS[i]
        bone_vec = joints[i] - joints[parent]
        
        # Inverse of rotation matrix is its transpose
        inv_parent_rot = global_rots[parent].T
        
        offsets[i] = inv_parent_rot @ bone_vec
        
    return offsets

def forward_kinematics(
    rotations: List[List[List[float]]],
    root_position: List[float],
    offsets: np.ndarray
) -> List[List[float]]:
    """
    Compute global joint positions from rotations and offsets.
    
    Args:
        rotations: (24, 3, 3) relative rotation matrices
        root_position: (3,) global position of the root joint
        offsets: (24, 3) bone offsets
        
    Returns:
        joints: (24, 3) global joint positions
    """
    rots = np.array(rotations)
    root_pos = np.array(root_position)
    
    joints = np.zeros((24, 3))
    global_rots = np.zeros((24, 3, 3))
    
    # Root
    joints[0] = root_pos
    global_rots[0] = rots[0]
    
    # Propagate
    for i in range(1, 24):
        parent = SMPL_PARENTS[i]
        
        # Global rotation
        global_rots[i] = global_rots[parent] @ rots[i]
        
        # Global position
        # Pos_i = Pos_parent + Rot_parent @ Offset_i
        joints[i] = joints[parent] + global_rots[parent] @ offsets[i]
        
    return joints.tolist()

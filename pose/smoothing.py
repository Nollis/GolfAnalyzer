import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import gaussian_filter1d
from typing import List, Optional

def smooth_pose_sequence(
    smpl_poses: List[List[List[List[float]]]], 
    sigma: float = 2.0
) -> List[List[List[List[float]]]]:
    """
    Smooth a sequence of SMPL poses using quaternion smoothing.
    
    Args:
        smpl_poses: List of N frames, each containing 24x3x3 rotation matrices.
        sigma: Standard deviation for Gaussian kernel (smoothing strength).
        
    Returns:
        List of N frames with smoothed rotation matrices.
    """
    if not smpl_poses:
        return []
        
    # Convert to numpy array: (N, 24, 3, 3)
    poses_np = np.array(smpl_poses)
    n_frames, n_joints, _, _ = poses_np.shape
    
    smoothed_poses = np.zeros_like(poses_np)
    
    # Process each joint independently
    for j in range(n_joints):
        # Extract rotation matrices for this joint across all frames: (N, 3, 3)
        joint_rots = poses_np[:, j, :, :]
        
        # Convert to quaternions: (N, 4)
        r = R.from_matrix(joint_rots)
        quats = r.as_quat()
        
        # Ensure continuity (handle double cover of SO(3))
        # If dot product between consecutive quats is negative, flip sign
        for i in range(1, n_frames):
            if np.dot(quats[i-1], quats[i]) < 0:
                quats[i] = -quats[i]
                
        # Apply Gaussian smoothing to quaternion components
        # mode='nearest' extends the edge values
        quats_smooth = gaussian_filter1d(quats, sigma=sigma, axis=0, mode='nearest')
        
        # Normalize back to unit quaternions
        norms = np.linalg.norm(quats_smooth, axis=1, keepdims=True)
        quats_smooth /= norms
        
        # Convert back to rotation matrices
        r_smooth = R.from_quat(quats_smooth)
        smoothed_poses[:, j, :, :] = r_smooth.as_matrix()
        
    return smoothed_poses.tolist()

import numpy as np
from typing import List, Tuple, Optional
from pose.kinematics import forward_kinematics, calculate_offsets_from_pose

# SMPL Joint Indices
# 16: L_Shoulder, 18: L_Elbow, 20: L_Wrist
# 17: R_Shoulder, 19: R_Elbow, 21: R_Wrist
IDX_L_SHOULDER = 16
IDX_L_ELBOW = 18
IDX_L_WRIST = 20
IDX_R_SHOULDER = 17
IDX_R_ELBOW = 19
IDX_R_WRIST = 21

def fit_plane(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit a plane to a set of 3D points using PCA (SVD).
    Returns (normal, centroid).
    """
    centroid = np.mean(points, axis=0)
    centered_points = points - centroid
    u, s, vh = np.linalg.svd(centered_points)
    # The normal is the last row of Vh (corresponding to smallest singular value)
    normal = vh[2, :]
    return normal, centroid

def project_point_to_plane(point: np.ndarray, normal: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    """Project a point onto a plane defined by normal and centroid."""
    v = point - centroid
    dist = np.dot(v, normal)
    projected = point - dist * normal
    return projected

def solve_two_bone_ik(
    root_pos: np.ndarray,
    effector_pos: np.ndarray,
    target_pos: np.ndarray,
    joint_pos: np.ndarray,
    epsilon: float = 1e-6
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simple analytical IK for a two-bone chain (e.g., Shoulder -> Elbow -> Wrist).
    Adjusts the joint (Elbow) position to reach target while preserving bone lengths.
    
    Args:
        root_pos: Shoulder position (fixed)
        effector_pos: Current Wrist position
        target_pos: Target Wrist position
        joint_pos: Current Elbow position
        
    Returns:
        new_joint_pos: New Elbow position
        new_effector_pos: New Wrist position (may differ from target if unreachable)
    """
    # Bone lengths
    L1 = np.linalg.norm(joint_pos - root_pos)
    L2 = np.linalg.norm(effector_pos - joint_pos)
    
    # Vector from root to target
    target_vec = target_pos - root_pos
    target_dist = np.linalg.norm(target_vec)
    
    # Check reachability
    if target_dist > (L1 + L2) - epsilon:
        # Target too far, fully extend
        direction = target_vec / (target_dist + epsilon)
        new_joint = root_pos + direction * L1
        new_effector = new_joint + direction * L2
        return new_joint, new_effector
    
    if target_dist < abs(L1 - L2) + epsilon:
        # Target too close (shouldn't happen often for arms), fold back
        # Just keep current pose or project? Let's just return current to be safe
        return joint_pos, effector_pos

    # Law of Cosines to find angle at Shoulder (alpha)
    # L2^2 = L1^2 + target_dist^2 - 2*L1*target_dist*cos(alpha)
    cos_alpha = (L1**2 + target_dist**2 - L2**2) / (2 * L1 * target_dist)
    # Clamp for safety
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    alpha = np.arccos(cos_alpha)
    
    # We need a plane for the arm triangle.
    # Use the original arm plane (Root, Joint, Effector) if possible.
    # If arm is straight, pick a default up vector.
    
    arm_vec_1 = joint_pos - root_pos
    arm_vec_2 = effector_pos - joint_pos
    
    # Normal of the current arm plane
    arm_plane_normal = np.cross(arm_vec_1, arm_vec_2)
    if np.linalg.norm(arm_plane_normal) < epsilon:
        # Arm is straight, pick an arbitrary vector perpendicular to target_vec
        # Try Y axis (up)
        idx_up = np.array([0, 1, 0])
        if abs(np.dot(target_vec / target_dist, idx_up)) > 0.9:
             idx_up = np.array([1, 0, 0]) # Switch to X if target is vertical
        arm_plane_normal = np.cross(target_vec, idx_up)
    
    arm_plane_normal = arm_plane_normal / (np.linalg.norm(arm_plane_normal) + epsilon)
    
    # Now we rotate the vector (Root -> Target) by alpha around the arm_plane_normal
    # to get the new Root -> Joint vector.
    
    # Rotation matrix (Rodrigues' rotation formula)
    # v_rot = v*cos(theta) + (k x v)*sin(theta) + k*(k.v)*(1-cos(theta))
    # Here v is target_vec normalized * L1
    
    v_base = target_vec / (target_dist + epsilon) * L1
    k = arm_plane_normal
    theta = alpha
    
    v_rot = v_base * np.cos(theta) + np.cross(k, v_base) * np.sin(theta) + k * np.dot(k, v_base) * (1 - np.cos(theta))
    
    new_joint = root_pos + v_rot
    new_effector = target_pos # We assume we can reach it now
    
    return new_joint, new_effector

def rotation_matrix_from_vectors(vec1, vec2):
    """Find the rotation matrix that aligns vec1 to vec2."""
    a, b = (vec1 / np.linalg.norm(vec1)), (vec2 / np.linalg.norm(vec2))
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    
    if s < 1e-6:
        # Vectors are parallel
        if c > 0:
            return np.eye(3)
        else:
            # Vectors are opposite, rotate 180 around any orthogonal axis
            # Find orthogonal
            if abs(a[0]) < 0.9:
                orth = np.cross(a, [1, 0, 0])
            else:
                orth = np.cross(a, [0, 1, 0])
            orth = orth / np.linalg.norm(orth)
            # 180 deg rotation around orth
            # R = I + 2*skew(orth)^2 ... actually simpler: -I + 2*outer(orth, orth)
            return -np.eye(3) + 2 * np.outer(orth, orth)

    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))
    return rotation_matrix

def get_global_rotations(smpl_pose: np.ndarray) -> List[np.ndarray]:
    """Compute global rotations for all joints."""
    global_rots = []
    # SMPL_PARENTS must be imported or defined. 
    # We'll define it locally to avoid circular imports if not available
    parents = [
        -1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19, 20, 21
    ]
    
    for i in range(24):
        if parents[i] == -1:
            global_rots.append(smpl_pose[i])
        else:
            global_rots.append(global_rots[parents[i]] @ smpl_pose[i])
            
    return global_rots

def enforce_swing_plane(
    joints_3d_frames: List[List[List[float]]], 
    smpl_pose_frames: List[List[List[List[float]]]], 
    lambda_strength: float = 0.4
) -> Tuple[List[List[List[float]]], List[List[List[List[float]]]]]:
    """
    Enforce swing plane constraint on a sequence of poses.
    
    Args:
        joints_3d_frames: List of (24, 3) joint positions per frame
        smpl_pose_frames: List of (24, 3, 3) rotation matrices per frame
        lambda_strength: Strength of correction (0.0 to 1.0)
        
    Returns:
        corrected_joints, corrected_smpl_poses
    """
    if not joints_3d_frames or not smpl_pose_frames:
        return joints_3d_frames, smpl_pose_frames
        
    n_frames = len(joints_3d_frames)
    
    # 1. Collect wrist points
    wrist_points = []
    for joints in joints_3d_frames:
        joints_np = np.array(joints)
        if len(joints_np) > IDX_R_WRIST:
            wrist_points.append(joints_np[IDX_L_WRIST])
            wrist_points.append(joints_np[IDX_R_WRIST])
            
    if len(wrist_points) < 10:
        return joints_3d_frames, smpl_pose_frames
        
    wrist_points_np = np.array(wrist_points)
    
    # 2. Fit Plane
    normal, centroid = fit_plane(wrist_points_np)
    
    corrected_joints_frames = []
    corrected_smpl_frames = []
    
    # SMPL Parents for local conversion
    parents = [
        -1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19, 20, 21
    ]
    
    for i in range(n_frames):
        joints = np.array(joints_3d_frames[i])
        smpl_pose = np.array(smpl_pose_frames[i])
        
        # Copy to avoid modifying original
        new_smpl_pose = smpl_pose.copy()
        
        # Compute Global Rotations for current frame
        global_rots = get_global_rotations(smpl_pose)
        
        # --- Left Arm ---
        l_shoulder_idx = IDX_L_SHOULDER
        l_elbow_idx = IDX_L_ELBOW
        l_wrist_idx = IDX_L_WRIST
        l_parent_idx = parents[l_shoulder_idx] # Collar
        
        l_shoulder_pos = joints[l_shoulder_idx]
        l_elbow_pos = joints[l_elbow_idx]
        l_wrist_pos = joints[l_wrist_idx]
        
        # Project wrist
        l_wrist_proj = project_point_to_plane(l_wrist_pos, normal, centroid)
        l_wrist_target = l_wrist_pos + (l_wrist_proj - l_wrist_pos) * lambda_strength
        
        # IK
        new_l_elbow_pos, new_l_wrist_pos = solve_two_bone_ik(l_shoulder_pos, l_wrist_pos, l_wrist_target, l_elbow_pos)
        
        # Vectors
        vec_upper_old = l_elbow_pos - l_shoulder_pos
        vec_upper_new = new_l_elbow_pos - l_shoulder_pos
        
        vec_forearm_old = l_wrist_pos - l_elbow_pos
        vec_forearm_new = new_l_wrist_pos - new_l_elbow_pos
        
        # 1. Update Shoulder Global Rotation
        # Rotation to align upper arm
        rot_diff_upper = rotation_matrix_from_vectors(vec_upper_old, vec_upper_new)
        l_shoulder_global_old = global_rots[l_shoulder_idx]
        l_shoulder_global_new = rot_diff_upper @ l_shoulder_global_old
        
        # 2. Update Elbow Global Rotation
        # The elbow moves AND rotates with the shoulder.
        # Intermediate global rotation of elbow (after shoulder update, before elbow update)
        # Assuming rigid connection, elbow global rot rotates by same rot_diff_upper
        l_elbow_global_intermediate = rot_diff_upper @ global_rots[l_elbow_idx]
        
        # Now rotate forearm to target
        # The forearm vector resulting from intermediate
        vec_forearm_intermediate = rot_diff_upper @ vec_forearm_old
        
        # Rotation to align forearm
        rot_diff_forearm = rotation_matrix_from_vectors(vec_forearm_intermediate, vec_forearm_new)
        l_elbow_global_new = rot_diff_forearm @ l_elbow_global_intermediate
        
        # 3. Convert to Local Rotations
        # Shoulder Local: inv(Parent_Global) @ Shoulder_Global
        l_parent_global = global_rots[l_parent_idx]
        new_smpl_pose[l_shoulder_idx] = l_parent_global.T @ l_shoulder_global_new
        
        # Elbow Local: inv(Shoulder_Global_New) @ Elbow_Global_New
        new_smpl_pose[l_elbow_idx] = l_shoulder_global_new.T @ l_elbow_global_new
        
        
        # --- Right Arm ---
        r_shoulder_idx = IDX_R_SHOULDER
        r_elbow_idx = IDX_R_ELBOW
        r_wrist_idx = IDX_R_WRIST
        r_parent_idx = parents[r_shoulder_idx]
        
        r_shoulder_pos = joints[r_shoulder_idx]
        r_elbow_pos = joints[r_elbow_idx]
        r_wrist_pos = joints[r_wrist_idx]
        
        r_wrist_proj = project_point_to_plane(r_wrist_pos, normal, centroid)
        r_wrist_target = r_wrist_pos + (r_wrist_proj - r_wrist_pos) * lambda_strength
        
        new_r_elbow_pos, new_r_wrist_pos = solve_two_bone_ik(r_shoulder_pos, r_wrist_pos, r_wrist_target, r_elbow_pos)
        
        vec_upper_old_r = r_elbow_pos - r_shoulder_pos
        vec_upper_new_r = new_r_elbow_pos - r_shoulder_pos
        
        vec_forearm_old_r = r_wrist_pos - r_elbow_pos
        vec_forearm_new_r = new_r_wrist_pos - new_r_elbow_pos
        
        rot_diff_upper_r = rotation_matrix_from_vectors(vec_upper_old_r, vec_upper_new_r)
        r_shoulder_global_old = global_rots[r_shoulder_idx]
        r_shoulder_global_new = rot_diff_upper_r @ r_shoulder_global_old
        
        r_elbow_global_intermediate = rot_diff_upper_r @ global_rots[r_elbow_idx]
        vec_forearm_intermediate_r = rot_diff_upper_r @ vec_forearm_old_r
        
        rot_diff_forearm_r = rotation_matrix_from_vectors(vec_forearm_intermediate_r, vec_forearm_new_r)
        r_elbow_global_new = rot_diff_forearm_r @ r_elbow_global_intermediate
        
        r_parent_global = global_rots[r_parent_idx]
        new_smpl_pose[r_shoulder_idx] = r_parent_global.T @ r_shoulder_global_new
        new_smpl_pose[r_elbow_idx] = r_shoulder_global_new.T @ r_elbow_global_new
        
        corrected_smpl_frames.append(new_smpl_pose.tolist())
        
        # Recompute FK
        # Use original offsets
        offsets = calculate_offsets_from_pose(joints.tolist(), smpl_pose.tolist())
        new_joints_fk = forward_kinematics(new_smpl_pose.tolist(), joints[0].tolist(), offsets)
        corrected_joints_frames.append(new_joints_fk)
        
    return corrected_joints_frames, corrected_smpl_frames


import json
import math
import numpy as np
from scipy.spatial.transform import Rotation as R

def apply_pose_corrections(poses_data: list, corrections: dict) -> list:
    """
    Apply rotation corrections to pose landmarks and SMPL matrices.
    """
    corrected = []
    
    # Mapping from SMPL joint indices to MediaPipe pivot landmarks
    SMPL_TO_MP_PIVOT = {
        16: 11, # L Shoulder
        17: 12, # R Shoulder
        18: 13, # L Elbow
        19: 14, # R Elbow
        1: 23,  # L Hip
        2: 24,  # R Hip
        4: 25,  # L Knee
        5: 26,  # R Knee
    }

    # Subtrees to rotate for each pivot (MediaPipe indices)
    MP_SUBTREES = {
        11: [13, 15, 17, 19, 21], # L Shoulder -> Arm
        12: [14, 16, 18, 20, 22], # R Shoulder -> Arm
        13: [15, 17, 19, 21],     # L Elbow -> Forearm
        14: [16, 18, 20, 22],     # R Elbow -> Forearm
        23: [25, 27, 29, 31],     # L Hip -> Leg
        24: [26, 28, 30, 32],     # R Hip -> Leg
        25: [27, 29, 31],         # L Knee -> Lower Leg
        26: [28, 30, 32],         # R Knee -> Lower Leg
    }
    
    for pose in poses_data:
        frame_idx = str(pose.get("frame_index", 0))
        
        if frame_idx not in corrections:
            corrected.append(pose)
            continue
        
        # Deep copy the pose
        new_pose = {
            "frame_index": pose.get("frame_index"),
            "timestamp_ms": pose.get("timestamp_ms"),
            "landmarks": [lm.copy() for lm in pose.get("landmarks", [])]
        }
        
        frame_corrections = corrections[frame_idx]
        landmarks = new_pose["landmarks"]
        
        # 1. Apply corrections to Landmarks (Hierarchical)
        for joint_idx_str, rot in frame_corrections.items():
            smpl_idx = int(joint_idx_str)
            
            if smpl_idx in SMPL_TO_MP_PIVOT:
                pivot_idx = SMPL_TO_MP_PIVOT[smpl_idx]
                
                if pivot_idx < len(landmarks):
                    pivot = landmarks[pivot_idx]
                    subtree_indices = MP_SUBTREES.get(pivot_idx, [])
                    
                    # Create rotation matrix
                    rx = math.radians(rot.get("x", 0))
                    ry = math.radians(rot.get("y", 0))
                    rz = math.radians(rot.get("z", 0))
                    
                    # Euler to Matrix (XYZ order matches frontend)
                    # Using scipy for consistent rotation
                    r = R.from_euler('xyz', [rx, ry, rz], degrees=False)
                    rot_mat = r.as_matrix()
                    
                    pivot_vec = np.array([pivot["x"], pivot["y"], pivot.get("z", 0)])
                    
                    for child_idx in subtree_indices:
                        if child_idx < len(landmarks):
                            child = landmarks[child_idx]
                            child_vec = np.array([child["x"], child["y"], child.get("z", 0)])
                            
                            # Rotate relative to pivot
                            rel_vec = child_vec - pivot_vec
                            rotated_vec = rot_mat @ rel_vec
                            new_vec = pivot_vec + rotated_vec
                            
                            child["x"] = float(new_vec[0])
                            child["y"] = float(new_vec[1])
                            child["z"] = float(new_vec[2])

        # 2. Apply corrections to SMPL Pose (Matrices)
        if "smpl_pose" in pose:
            try:
                # smpl_pose is a list of 24 3x3 matrices
                smpl_pose = np.array(pose["smpl_pose"])
                
                for joint_idx_str, rot in frame_corrections.items():
                    joint_idx = int(joint_idx_str)
                    if joint_idx < len(smpl_pose):
                        # Get current rotation matrix
                        current_mat = smpl_pose[joint_idx]
                        
                        # Create correction rotation
                        rx = rot.get("x", 0)
                        ry = rot.get("y", 0)
                        rz = rot.get("z", 0)
                        
                        correction_rot = R.from_euler('xyz', [rx, ry, rz], degrees=True)
                        correction_mat = correction_rot.as_matrix()
                        
                        # Apply correction: R_new = R_old @ R_correction
                        new_mat = current_mat @ correction_mat
                        smpl_pose[joint_idx] = new_mat
                
                new_pose["smpl_pose"] = smpl_pose.tolist()
            except Exception as e:
                print(f"Error applying SMPL corrections: {e}")
                # Keep original if failed
                new_pose["smpl_pose"] = pose["smpl_pose"]
        
        corrected.append(new_pose)
    
    return corrected

# Mock data
mock_pose = {
    "frame_index": 0,
    "timestamp_ms": 0,
    "landmarks": [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} for _ in range(33)],
    "smpl_pose": [np.eye(3).tolist() for _ in range(24)]
}

# Setup: L Shoulder at (0,0), L Elbow at (1,0)
mock_pose["landmarks"][11] = {"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} # L Shoulder
mock_pose["landmarks"][13] = {"x": 1.0, "y": 0.0, "z": 0.0, "visibility": 1.0} # L Elbow

mock_corrections = {
    "0": {
        "16": {"x": 0, "y": 0, "z": 90} # Rotate left shoulder 90 deg Z (should move elbow to (0,1))
    }
}

# Run test
corrected = apply_pose_corrections([mock_pose], mock_corrections)
new_elbow = corrected[0]["landmarks"][13]
print(f"Original Elbow: (1.0, 0.0)")
print(f"New Elbow: ({new_elbow['x']:.2f}, {new_elbow['y']:.2f})")

# Check SMPL
print("Corrected SMPL pose shape:", np.array(corrected[0]["smpl_pose"]).shape)

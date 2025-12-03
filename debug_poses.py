import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import sys
import os

def analyze_pose(session_id):
    file_path = f"c:/Projekt/GolfAnalyzer/videos/{session_id}_poses.json"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} frames.")
    
    # Analyze the first valid frame
    for i, frame in enumerate(data):
        if 'smpl_pose' in frame and frame['smpl_pose']:
            print(f"\nAnalyzing Frame {i}:")
            smpl_pose = np.array(frame['smpl_pose'])
            print(f"SMPL Pose Shape: {smpl_pose.shape}")
            
            # Root Rotation (Index 0)
            root_mat = smpl_pose[0]
            r = R.from_matrix(root_mat)
            euler = r.as_euler('xyz', degrees=True)
            print(f"Root Rotation (Euler XYZ): {euler}")
            print(f"Root Matrix:\n{root_mat}")
            
            # Left Shoulder (Index 16 in SMPL? No, check mapping)
            # Mapping from SMPLViewer:
            # 13: "mixamorigLeftShoulder" -> SMPL Index?
            # The mapping in SMPLViewer was:
            # 13: "mixamorigLeftShoulder" (Index 13 in loop? No, loop is 0..23)
            # Wait, the loop in SMPLViewer iterates 0..23.
            # The SMPL_TO_BONE_NAME keys are the SMPL indices.
            # 13: "mixamorigLeftShoulder"
            
            l_shoulder_idx = 13
            l_shoulder_mat = smpl_pose[l_shoulder_idx]
            r_ls = R.from_matrix(l_shoulder_mat)
            euler_ls = r_ls.as_euler('xyz', degrees=True)
            print(f"L Shoulder (idx 13) Rotation (Euler XYZ): {euler_ls}")
            
            break

if __name__ == "__main__":
    # Use the session ID from the logs
    session_id = "f8d06665-4e07-40a2-a3a0-c7050ad854f9"
    analyze_pose(session_id)

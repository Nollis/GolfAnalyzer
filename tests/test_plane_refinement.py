import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pose.refinement.plane_of_swing import enforce_swing_plane, fit_plane

def create_dummy_data(n_frames=20):
    """Create dummy swing data (randomized around a plane)."""
    joints_frames = []
    smpl_frames = []
    
    # Define a true plane: Z = 0.5 * X
    # Wrist points will be noisy around this
    
    for i in range(n_frames):
        # Create a basic skeleton
        # Root at 0,0,0
        # Shoulder at 0, 1.5, 0
        # Arm extending out
        
        t = i / n_frames
        x = np.sin(t * np.pi) # Swing arc
        y = 1.0 - 0.5 * np.cos(t * np.pi)
        z_ideal = 0.5 * x
        
        # Add noise to Z
        z_noisy = z_ideal + np.random.normal(0, 0.1)
        
        joints = np.zeros((24, 3))
        joints[0] = [0, 0, 0] # Pelvis
        joints[16] = [0.2, 1.5, 0] # L Shoulder
        joints[18] = [0.4, 1.5, 0] # L Elbow (dummy)
        joints[20] = [x, y, z_noisy] # L Wrist
        
        joints[17] = [-0.2, 1.5, 0] # R Shoulder
        joints[19] = [-0.4, 1.5, 0] # R Elbow
        joints[21] = [x-0.1, y-0.1, z_noisy] # R Wrist
        
        joints_frames.append(joints.tolist())
        
        # Dummy rotations (identity)
        smpl_frames.append(np.tile(np.eye(3), (24, 1, 1)).tolist())
        
    return joints_frames, smpl_frames

def test_plane_refinement():
    print("Generating dummy data...")
    joints, smpl = create_dummy_data()
    
    # Measure initial variance from plane
    wrists = []
    for j in joints:
        wrists.append(j[20])
        wrists.append(j[21])
    wrists = np.array(wrists)
    
    normal, centroid = fit_plane(wrists)
    initial_dists = []
    for w in wrists:
        dist = np.dot(w - centroid, normal)
        initial_dists.append(abs(dist))
    print(f"Initial mean distance from plane: {np.mean(initial_dists):.4f}")
    
    print("Applying refinement...")
    new_joints, new_smpl = enforce_swing_plane(joints, smpl, lambda_strength=0.8)
    
    # Measure new variance
    new_wrists = []
    for j in new_joints:
        new_wrists.append(j[20])
        new_wrists.append(j[21])
    new_wrists = np.array(new_wrists)
    
    # Fit new plane (should be similar)
    new_normal, new_centroid = fit_plane(new_wrists)
    
    new_dists = []
    for w in new_wrists:
        # Check distance to ORIGINAL plane to see convergence
        dist = np.dot(w - centroid, normal)
        new_dists.append(abs(dist))
        
    print(f"Refined mean distance from original plane: {np.mean(new_dists):.4f}")
    
    if np.mean(new_dists) < np.mean(initial_dists):
        print("SUCCESS: Variance reduced.")
    else:
        print("FAILURE: Variance did not reduce.")

if __name__ == "__main__":
    test_plane_refinement()

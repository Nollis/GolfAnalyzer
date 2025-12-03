
import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from pose.presets import address_blend

def test_blending():
    print("Loading address pose...")
    address_blend.load_address_pose()
    
    if address_blend.ADDRESS_POSE is None:
        print("FAILED: Address pose not loaded")
        return

    print(f"Address pose loaded. Shape: {len(address_blend.ADDRESS_POSE)} x {len(address_blend.ADDRESS_POSE[0])} x {len(address_blend.ADDRESS_POSE[0][0])}")
    
    # Create a dummy DTL pose (identity matrices)
    dtl_pose = [np.eye(3).tolist() for _ in range(24)]
    
    # Blend
    print("Blending with identity pose...")
    blended = address_blend.blend_with_address(dtl_pose)
    
    # Check if blending happened
    # Torso joints should be blended (not identity)
    # Pelvis is index 0
    pelvis_blended = np.array(blended[0])
    pelvis_identity = np.eye(3)
    
    if np.allclose(pelvis_blended, pelvis_identity):
        print("FAILED: Pelvis (torso) was not blended (still identity)")
    else:
        print("SUCCESS: Pelvis was blended")
        print("Blended Pelvis:\n", pelvis_blended)
        
    # Check arms (should be identity / 0 alpha)
    # L Shoulder is 16
    shoulder_blended = np.array(blended[16])
    if np.allclose(shoulder_blended, pelvis_identity):
        print("SUCCESS: Shoulder was NOT blended (remained identity)")
    else:
        print("FAILED: Shoulder was blended")

if __name__ == "__main__":
    test_blending()

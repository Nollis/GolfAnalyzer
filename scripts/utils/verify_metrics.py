
from pose.metrics import MetricsCalculator, IDX_L_WRIST, IDX_L_SHOULDER, IDX_R_SHOULDER, IDX_L_HIP

def test_metrics():
    calc = MetricsCalculator()
    
    # Mock frame with 3D landmarks (HybrIK style)
    # Right-handed golfer at Top of Backswing
    # Hands high (wrist Y < shoulder Y)
    # Hands wide/deep
    
    # Y is passing, X is lateral, Z is depth
    
    # Shoulder height: Y = -0.5
    # Hip height: Y = 0.0
    # Torso length = 0.5
    
    # Wrist height: Y = -0.7 (High, 0.2 above shoulder)
    # Diff = -0.5 - (-0.7) = 0.2
    # Index = 0.2 / 0.5 = 0.4 (High)
    
    # Chest center: X=0, Z=0
    # Wrist Z: 0.3 (deep)
    # Wrist X: -0.2 (behind)
    
    frame = {
        "landmarks_3d": [
            *[{} for _ in range(30)], # Fill dummy
        ]
    }
    
    # Populate specific indices
    # IDX_L_WRIST = 15
    frame["landmarks_3d"][IDX_L_WRIST] = {"x": -0.2, "y": -0.7, "z": 0.3, "visibility": 0.9}
    
    # IDX_L_SHOULDER = 11
    frame["landmarks_3d"][IDX_L_SHOULDER] = {"x": -0.2, "y": -0.5, "z": 0.0, "visibility": 0.9}
    
    # IDX_R_SHOULDER = 12
    frame["landmarks_3d"][IDX_R_SHOULDER] = {"x": 0.2, "y": -0.5, "z": 0.0, "visibility": 0.9}
    
    # IDX_L_HIP = 23
    frame["landmarks_3d"][IDX_L_HIP] = {"x": -0.1, "y": 0.0, "z": 0.0, "visibility": 0.9}
    
    print("Testing Hand Height...")
    hh = calc._compute_hand_height(frame, "Right", True)
    print(f"Hand Height Index: {hh} (Expected ~0.4)")
    
    print("Testing Hand Width...")
    hw = calc._compute_hand_width(frame, "Right", True)
    print(f"Hand Width Index: {hw}")
    
    # Test None case
    hh_none = calc._compute_hand_height({}, "Right", True)
    print(f"Hand Height (None): {hh_none}")

if __name__ == "__main__":
    test_metrics()

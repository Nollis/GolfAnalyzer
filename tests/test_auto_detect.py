from pose.metrics import MetricsCalculator
from app.schemas import SwingMetrics, SwingPhases
from pose.types import FramePose, Point3D

def test_auto_detection():
    calc = MetricsCalculator()
    
    # Test Handedness Detection
    # Mock poses: Address (frame 0) -> Top (frame 10)
    # Right-handed: Hands move RIGHT (positive X)
    
    # Address: Hands at center (0.5)
    address_pose = FramePose(timestamp_ms=0, landmarks=[Point3D(0,0,0,0)]*33)
    address_pose.landmarks[15] = Point3D(0.5, 0.5, 0, 0.9) # Left wrist
    address_pose.landmarks[16] = Point3D(0.5, 0.5, 0, 0.9) # Right wrist
    
    # Top: Hands at right (0.8)
    top_pose = FramePose(timestamp_ms=1000, landmarks=[Point3D(0,0,0,0)]*33)
    top_pose.landmarks[15] = Point3D(0.8, 0.2, 0, 0.9)
    top_pose.landmarks[16] = Point3D(0.8, 0.2, 0, 0.9)
    
    poses = [address_pose] * 20
    poses[10] = top_pose
    phases = SwingPhases(address_frame=0, top_frame=10, impact_frame=15, finish_frame=20)
    
    handedness = calc.detect_handedness(poses, phases)
    print(f"Detected Handedness (Expected Right): {handedness}")
    assert handedness == "Right"
    
    # Test Left-handed
    # Top: Hands at left (0.2)
    top_pose_left = FramePose(timestamp_ms=1000, landmarks=[Point3D(0,0,0,0)]*33)
    top_pose_left.landmarks[15] = Point3D(0.2, 0.2, 0, 0.9)
    top_pose_left.landmarks[16] = Point3D(0.2, 0.2, 0, 0.9)
    
    poses_left = [address_pose] * 20
    poses_left[10] = top_pose_left
    
    handedness_left = calc.detect_handedness(poses_left, phases)
    print(f"Detected Handedness (Expected Left): {handedness_left}")
    assert handedness_left == "Left"

    # Test Club Type Estimation
    # Driver: > 1000ms backswing
    metrics_driver = calc._empty_metrics()
    metrics_driver.backswing_duration_ms = 1100
    club = calc.estimate_club_type(metrics_driver)
    print(f"Estimated Club (Expected Driver): {club}")
    assert club == "Driver"
    
    # Iron: 800-1000ms
    metrics_iron = calc._empty_metrics()
    metrics_iron.backswing_duration_ms = 900
    club = calc.estimate_club_type(metrics_iron)
    print(f"Estimated Club (Expected Iron): {club}")
    assert club == "Iron"
    
    # Wedge: < 800ms
    metrics_wedge = calc._empty_metrics()
    metrics_wedge.backswing_duration_ms = 700
    club = calc.estimate_club_type(metrics_wedge)
    print(f"Estimated Club (Expected Wedge): {club}")
    assert club == "Wedge"

if __name__ == "__main__":
    test_auto_detection()

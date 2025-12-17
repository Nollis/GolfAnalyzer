import sys
import os
import cv2

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pose.legacy_mediapipe import MediaPipeWrapper
from pose.swing_detection import SwingDetector
from pose.metrics import MetricsCalculator

def main(video_path):
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        return

    print(f"Processing {video_path}...")

    # 1. Pose
    print("Extracting poses...")
    mp_wrapper = MediaPipeWrapper()
    poses = mp_wrapper.extract_poses_from_video(video_path)
    print(f"Extracted {len(poses)} frames with poses.")

    # FPS
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if fps <= 0: fps = 30.0
    print(f"FPS: {fps}")

    # 2. Phases
    print("Detecting phases...")
    detector = SwingDetector()
    phases = detector.detect_swing_phases(poses, fps)
    print(f"Phases: {phases}")

    # 3. Metrics
    print("Computing metrics...")
    calculator = MetricsCalculator()
    metrics = calculator.compute_metrics(poses, phases, fps)
    print(f"Metrics: {metrics}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/test_pipeline_manual.py <video_path>")
    else:
        main(sys.argv[1])

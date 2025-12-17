import mediapipe as mp
import cv2
import numpy as np
from typing import List, Optional, NamedTuple
from pose.types import Point3D, FramePose

class MediaPipeWrapper:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.6
        )

    def extract_poses_from_video(self, video_path: str) -> List[FramePose]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video at {video_path}")

        frame_poses = []
        frame_idx = 0

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            # Convert the BGR image to RGB.
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process the image and find poses
            results = self.pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = []
                for lm in results.pose_landmarks.landmark:
                    landmarks.append(Point3D(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility))
                
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                frame_poses.append(FramePose(frame_index=frame_idx, timestamp_ms=timestamp_ms, landmarks=landmarks))
            else:
                # Handle missing pose? For now, just append None or skip
                # Appending empty list or None might break downstream. 
                # Let's append a FramePose with empty landmarks or interpolate later.
                # For simplicity, we'll skip or handle in detection.
                pass

            frame_idx += 1

        cap.release()
        return frame_poses

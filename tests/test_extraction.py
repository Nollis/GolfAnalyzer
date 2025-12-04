import cv2
import os

def test_extraction():
    video_dir = "videos"
    if not os.path.exists(video_dir):
        print(f"Directory {video_dir} does not exist")
        return

    # Find the first mp4 file
    video_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
    if not video_files:
        print("No video files found in videos/")
        return

    video_file = video_files[0]
    video_path = os.path.join(video_dir, video_file)
    print(f"Testing extraction from: {video_path}")
    print(f"Absolute path: {os.path.abspath(video_path)}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Failed to open video file")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"✅ Video opened. Total frames: {total_frames}")

    # Try to read frame 0
    ret, frame = cap.read()
    if ret:
        print("✅ Successfully read frame 0")
        out_path = os.path.join(video_dir, "test_frame.jpg")
        cv2.imwrite(out_path, frame)
        print(f"✅ Saved test frame to {out_path}")
    else:
        print("❌ Failed to read frame 0")

    cap.release()

if __name__ == "__main__":
    test_extraction()

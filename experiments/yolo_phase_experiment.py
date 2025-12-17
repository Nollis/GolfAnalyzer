
import cv2
import time
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from scipy.signal import savgol_filter


def smooth_savgol(data: list, window_size: int = 7, poly_order: int = 2) -> np.ndarray:
    """
    Apply Savitzky-Golay filter for smoothing.
    Better at preserving sharp transitions than moving average.
    """
    if len(data) < window_size:
        return np.array(data)
    
    # Ensure window_size is odd
    if window_size % 2 == 0:
        window_size += 1
    
    return savgol_filter(data, window_size, poly_order)


def detect_phases_improved(wrist_ys: list, fps: float = 30.0) -> dict:
    """
    Improved phase detection using multiple signals.
    
    Strategy:
    - Address: First stable position (max Y before backswing)
    - Top: First local minimum (hands highest) after significant rise
    - Impact: Maximum Y (hands lowest) in the downswing window, confirmed by velocity peak
    - Finish: Hands highest after impact
    
    Args:
        wrist_ys: List of normalized wrist Y positions (0=top, 1=bottom)
        fps: Frames per second of the video
        
    Returns:
        Dictionary with phase frame indices
    """
    total_frames = len(wrist_ys)
    if total_frames < 10:
        return {"address": 0, "top": 0, "impact": 0, "finish": 0}
    
    # 1. Apply Savgol smoothing (better for preserving peaks)
    smooth_y = smooth_savgol(wrist_ys, window_size=7, poly_order=2)
    
    # 2. Calculate velocity and acceleration
    velocity = np.gradient(smooth_y)
    acceleration = np.gradient(velocity)
    
    # Also smooth the velocity for cleaner peak detection
    smooth_velocity = smooth_savgol(velocity, window_size=5, poly_order=2)
    
    # === DETECT TOP OF BACKSWING ===
    # Find first significant local minimum (hands at highest point)
    # Velocity crosses from negative (going up) to positive (going down)
    
    address_y = smooth_y[0]
    threshold_rise = 0.08  # Must rise at least 8% from start
    
    top_frame = 0
    for i in range(5, total_frames - 5):
        # Check for significant rise from address
        if address_y - smooth_y[i] > threshold_rise:
            # Look for velocity zero-crossing (neg -> pos)
            if velocity[i-1] <= 0 and velocity[i] > 0:
                # Confirm it's a real peak by checking surrounding values
                if smooth_y[i] < smooth_y[i-3] and smooth_y[i] < smooth_y[i+3]:
                    top_frame = i
                    break
    
    # Fallback: find global minimum in first 60% of video
    if top_frame == 0:
        search_end = int(total_frames * 0.6)
        top_frame = int(np.argmin(smooth_y[:search_end]))
    
    # === DETECT ADDRESS ===
    # Find the stable low position (max Y) before backswing begins
    # Look backwards from top to find where hands were lowest
    
    address_frame = 0
    search_start = max(0, top_frame - int(fps * 2))  # Up to 2 seconds before top
    
    max_y_before_top = -1.0
    for i in range(search_start, top_frame):
        if smooth_y[i] > max_y_before_top:
            max_y_before_top = smooth_y[i]
            address_frame = i
    
    # === DETECT IMPACT ===
    # Impact is when hands reach their LOWEST point (maximum Y) in the downswing
    # Use multiple signals for robustness:
    # 1. Maximum Y value in the downswing window
    # 2. Peak positive velocity (fastest descent)
    # 3. Sharp deceleration after peak velocity
    
    # Define search window for downswing (top + 5 frames to top + 0.5 seconds)
    search_start = top_frame + 3
    search_end = min(total_frames - 5, top_frame + int(fps * 0.5))  # Max 0.5s downswing
    
    if search_end <= search_start:
        search_end = min(total_frames - 1, search_start + 15)
    
    # Method 1: Find maximum Y (hands lowest)
    max_y_downswing = -1.0
    impact_by_position = search_start
    
    for i in range(search_start, search_end):
        if smooth_y[i] > max_y_downswing:
            max_y_downswing = smooth_y[i]
            impact_by_position = i
        # Early exit: if hands have risen significantly, we've passed impact
        elif max_y_downswing > 0 and max_y_downswing - smooth_y[i] > 0.04:
            break
    
    # Method 2: Find peak velocity (maximum positive velocity = fastest descent)
    velocity_window = smooth_velocity[search_start:search_end]
    if len(velocity_window) > 0:
        peak_velocity_idx = np.argmax(velocity_window)
        impact_by_velocity = search_start + peak_velocity_idx
    else:
        impact_by_velocity = impact_by_position
    
    # Combine signals: prefer position-based, but validate with velocity
    # If they differ by more than 3 frames, use a weighted average
    if abs(impact_by_position - impact_by_velocity) <= 3:
        impact_frame = impact_by_position  # Position is reliable
    else:
        # Use position but adjust slightly toward velocity peak
        impact_frame = int(0.7 * impact_by_position + 0.3 * impact_by_velocity)
    
    # Final adjustment: check if the frame after has an even lower hand position
    # This catches the "off by 1" error
    if impact_frame + 1 < total_frames:
        if smooth_y[impact_frame + 1] >= smooth_y[impact_frame]:
            # Next frame has hands even lower or same - that's the actual impact
            impact_frame = impact_frame + 1
    
    # === DETECT FINISH ===
    # Hands reach highest point (minimum Y) after impact
    
    finish_frame = total_frames - 1
    min_y_after_impact = 1.0
    
    for i in range(impact_frame + 3, total_frames):
        if smooth_y[i] < min_y_after_impact:
            min_y_after_impact = smooth_y[i]
            finish_frame = i
    
    # === SAFETY CHECKS ===
    # Ensure chronological order
    if top_frame <= address_frame:
        top_frame = address_frame + 5
    if impact_frame <= top_frame:
        impact_frame = top_frame + 5
    if finish_frame <= impact_frame:
        finish_frame = impact_frame + 5
    
    # Clamp to valid range
    finish_frame = min(finish_frame, total_frames - 1)
    impact_frame = min(impact_frame, finish_frame - 1)
    top_frame = min(top_frame, impact_frame - 1)
    address_frame = min(address_frame, top_frame - 1)
    
    return {
        "address": max(0, address_frame),
        "top": max(0, top_frame),
        "impact": max(0, impact_frame),
        "finish": max(0, finish_frame)
    }


def run_experiment(video_path: str):
    print(f"Loading YOLOv8-pose model...")
    # Use 'yolov8n-pose.pt' for maximum speed, 'yolov8m-pose.pt' for balance
    model = YOLO('yolov8n-pose.pt') 
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return
    
    # Get video FPS
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    wrist_ys = []  # Y coordinate of wrists (average)
    
    # YOLO Keypoint Indices (COCO format):
    # 9: left_wrist, 10: right_wrist
    IDX_L_WRIST = 9
    IDX_R_WRIST = 10
    
    print("Processing video frames...")
    start_time = time.time()
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Run inference
        results = model(frame, verbose=False)
        
        # Extract keypoints
        if results and len(results) > 0:
            keypoints = results[0].keypoints.xyn.cpu().numpy()
            
            if len(keypoints) > 0 and len(keypoints[0]) > 10:
                kpts = keypoints[0]
                
                l_wrist = kpts[IDX_L_WRIST]
                r_wrist = kpts[IDX_R_WRIST]
                
                # Average Y (0 is top, 1 is bottom)
                valid_cnt = 0
                y_sum = 0
                
                if l_wrist[0] > 0 and l_wrist[1] > 0:
                    y_sum += l_wrist[1]
                    valid_cnt += 1
                if r_wrist[0] > 0 and r_wrist[1] > 0:
                    y_sum += r_wrist[1]
                    valid_cnt += 1
                    
                if valid_cnt > 0:
                    wrist_ys.append(y_sum / valid_cnt)
                else:
                    wrist_ys.append(wrist_ys[-1] if wrist_ys else 0.5)
            else:
                wrist_ys.append(wrist_ys[-1] if wrist_ys else 0.5)
        else:
            wrist_ys.append(wrist_ys[-1] if wrist_ys else 0.5)
             
        frame_count += 1
        if frame_count % 10 == 0:
            print(f"Processed {frame_count} frames...", end='\r')
    
    cap.release()
            
    end_time = time.time()
    duration = end_time - start_time
    processing_fps = frame_count / duration
    
    print(f"\nAnalysis complete.")
    print(f"Total Frames: {frame_count}")
    print(f"Video FPS: {video_fps:.1f}")
    print(f"Processing Time: {duration:.2f}s")
    print(f"Processing FPS: {processing_fps:.2f}")
    
    # Run improved phase detection
    phases = detect_phases_improved(wrist_ys, fps=video_fps)
            
    print("-" * 40)
    print(f"DETECTED PHASES (YOLOv8 + Improved Heuristics)")
    print(f"  Address: Frame {phases['address']}")
    print(f"  Top:     Frame {phases['top']}")
    print(f"  Impact:  Frame {phases['impact']}")
    print(f"  Finish:  Frame {phases['finish']}")
    print("-" * 40)
    
    # Calculate tempo metrics
    backswing_frames = phases['top'] - phases['address']
    downswing_frames = phases['impact'] - phases['top']
    
    if downswing_frames > 0:
        tempo_ratio = backswing_frames / downswing_frames
        backswing_time = backswing_frames / video_fps
        downswing_time = downswing_frames / video_fps
        
        print(f"\nTEMPO ANALYSIS:")
        print(f"  Backswing: {backswing_frames} frames ({backswing_time:.2f}s)")
        print(f"  Downswing: {downswing_frames} frames ({downswing_time:.2f}s)")
        print(f"  Tempo Ratio: {tempo_ratio:.2f}:1")
        print(f"  (Pro average: ~3:1)")
    
    return phases

if __name__ == "__main__":
    # Determine project root (parent of experiments dir)
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    
    # Target specific video
    target_video = "5b9ef310-ea6c-432b-b020-d38594f7ff2c.mp4"
    
    # Check potential paths
    possible_paths = [
        # Relative to CWD (if running from root)
        Path("videos") / target_video,
        # Relative to script (if running from experiments)
        project_root / "videos" / target_video,
        # Absolute path (just in case)
        Path(r"c:\Projekt\GolfAnalyzer\videos") / target_video
    ]
    
    VIDEO_PATH = None
    for p in possible_paths:
        if p.exists():
            VIDEO_PATH = str(p)
            break
            
    if not VIDEO_PATH:
        print("Could not find target video. searching for any mp4...")
        # Fallback search
        for pattern in ["videos/*.mp4", "../videos/*.mp4"]:
            import glob
            matches = glob.glob(pattern)
            if matches:
                VIDEO_PATH = matches[0]
                break
    
    if VIDEO_PATH:
        print(f"Running experiment on: {VIDEO_PATH}")
        run_experiment(VIDEO_PATH)
    else:
        print("Error: No video file found for testing.")

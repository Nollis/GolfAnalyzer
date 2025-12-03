"""
SMPL-based pose extraction using HybrIK.

This module provides anatomically-correct 3D pose estimation using
SMPL body mesh reconstruction, which is more accurate than pure
keypoint detection for golf swing analysis.

Benefits over keypoint-based methods:
- Anatomically correct poses (joints can't bend impossibly)
- Better occlusion handling (mesh infers hidden parts)
- Direct joint rotation angles (no atan2 needed)
- Consistent body shape across frames
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Add HybrIK repo to path - adjust path for GolfAnalyzer structure
HYBRIK_REPO = Path(__file__).parent.parent / "hybrik_repo"
if HYBRIK_REPO.exists() and str(HYBRIK_REPO) not in sys.path:
    sys.path.insert(0, str(HYBRIK_REPO))

# SMPL Joint indices (24 joints)
SMPL_JOINTS = {
    "pelvis": 0,
    "l_hip": 1,
    "r_hip": 2,
    "spine1": 3,
    "l_knee": 4,
    "r_knee": 5,
    "spine2": 6,
    "l_ankle": 7,
    "r_ankle": 8,
    "spine3": 9,
    "l_foot": 10,
    "r_foot": 11,
    "neck": 12,
    "l_collar": 13,
    "r_collar": 14,
    "head": 15,
    "l_shoulder": 16,
    "r_shoulder": 17,
    "l_elbow": 18,
    "r_elbow": 19,
    "l_wrist": 20,
    "r_wrist": 21,
    "l_hand": 22,
    "r_hand": 23,
}

# HybrIK outputs 29 joints, mapping to our needs
HYBRIK_29_JOINTS = {
    "pelvis": 0,
    "l_hip": 1,
    "r_hip": 2,
    "spine1": 3,
    "l_knee": 4,
    "r_knee": 5,
    "spine2": 6,
    "l_ankle": 7,
    "r_ankle": 8,
    "spine3": 9,
    "l_foot": 10,
    "r_foot": 11,
    "neck": 12,
    "l_collar": 13,
    "r_collar": 14,
    "jaw": 15,
    "l_shoulder": 16,
    "r_shoulder": 17,
    "l_elbow": 18,
    "r_elbow": 19,
    "l_wrist": 20,
    "r_wrist": 21,
    "l_thumb": 22,
    "r_thumb": 23,
    "head": 24,
    "l_middle": 25,
    "r_middle": 26,
    "l_toe": 27,
    "r_toe": 28,
}

# Mapping from SMPL joints to MediaPipe-like indices for compatibility
SMPL_TO_MEDIAPIPE = {
    0: 23,   # pelvis -> left_hip (approximate)
    1: 23,   # l_hip -> left_hip
    2: 24,   # r_hip -> right_hip
    4: 25,   # l_knee -> left_knee
    5: 26,   # r_knee -> right_knee
    7: 27,   # l_ankle -> left_ankle
    8: 28,   # r_ankle -> right_ankle
    12: 0,   # neck -> nose (approximate)
    16: 11,  # l_shoulder -> left_shoulder
    17: 12,  # r_shoulder -> right_shoulder
    18: 13,  # l_elbow -> left_elbow
    19: 14,  # r_elbow -> right_elbow
    20: 15,  # l_wrist -> left_wrist
    21: 16,  # r_wrist -> right_wrist
}

# Check if HybrIK is available
HYBRIK_AVAILABLE = False
try:
    import torch
    from torchvision import transforms as T
    from torchvision.models.detection import fasterrcnn_resnet50_fpn
    from easydict import EasyDict as edict
    
    from hybrik.models import builder
    from hybrik.utils.config import update_config
    from hybrik.utils.presets import SimpleTransform3DSMPLCam
    from hybrik.utils.vis import get_max_iou_box, get_one_box
    
    HYBRIK_AVAILABLE = True
    logger.info("HybrIK successfully imported")
except ImportError as e:
    logger.warning(f"HybrIK not available: {e}")


class HybrIKExtractor:
    """
    Extract 3D poses using HybrIK SMPL-based mesh reconstruction.
    """
    
    def __init__(self, device: str = "cuda"):
        """
        Initialize HybrIK pose extractor.
        
        Args:
            device: "cuda" or "cpu"
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        self.hybrik_model = None
        self.det_model = None
        self.transformation = None
        self.cfg = None
        self._loaded = False
        
        # Paths
        self.cfg_file = HYBRIK_REPO / "configs" / "256x192_adam_lr1e-3-hrw48_cam_2x_w_pw3d_3dhp.yaml"
        self.ckpt_path = HYBRIK_REPO / "pretrained_models" / "hybrik_hrnet.pth"
        
    def load_model(self) -> bool:
        """
        Load the HybrIK model and detector.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if self._loaded:
            return True
            
        if not HYBRIK_AVAILABLE:
            logger.error("HybrIK not installed")
            return False
        
        if not self.ckpt_path.exists():
            logger.error(f"HybrIK checkpoint not found: {self.ckpt_path}")
            return False
            
        # HybrIK uses relative paths for model files, so we need to change to its directory
        import os
        original_cwd = os.getcwd()
        
        try:
            # Change to HybrIK repo directory (required for relative path model files)
            os.chdir(HYBRIK_REPO)
            logger.info(f"Loading HybrIK model from {self.ckpt_path}...")
            
            # Load config
            self.cfg = update_config(str(self.cfg_file))
            
            # Setup transformation
            bbox_3d_shape = getattr(self.cfg.MODEL, 'BBOX_3D_SHAPE', (2000, 2000, 2000))
            bbox_3d_shape = [item * 1e-3 for item in bbox_3d_shape]
            dummy_set = edict({
                'joint_pairs_17': None,
                'joint_pairs_24': None,
                'joint_pairs_29': None,
                'bbox_3d_shape': bbox_3d_shape
            })
            
            self.transformation = SimpleTransform3DSMPLCam(
                dummy_set, 
                scale_factor=self.cfg.DATASET.SCALE_FACTOR,
                color_factor=self.cfg.DATASET.COLOR_FACTOR,
                occlusion=self.cfg.DATASET.OCCLUSION,
                input_size=self.cfg.MODEL.IMAGE_SIZE,
                output_size=self.cfg.MODEL.HEATMAP_SIZE,
                depth_dim=self.cfg.MODEL.EXTRA.DEPTH_DIM,
                bbox_3d_shape=bbox_3d_shape,
                rot=self.cfg.DATASET.ROT_FACTOR, 
                sigma=self.cfg.MODEL.EXTRA.SIGMA,
                train=False, 
                add_dpg=False,
                loss_type=self.cfg.LOSS['TYPE']
            )
            
            # Load person detector
            logger.info("Loading person detector...")
            self.det_model = fasterrcnn_resnet50_fpn(pretrained=True)
            self.det_model.to(self.device)
            self.det_model.eval()
            
            # Load HybrIK model
            logger.info("Loading HybrIK pose model...")
            self.hybrik_model = builder.build_sppe(self.cfg.MODEL)
            
            save_dict = torch.load(str(self.ckpt_path), map_location='cpu')
            if isinstance(save_dict, dict) and 'model' in save_dict:
                model_dict = save_dict['model']
                self.hybrik_model.load_state_dict(model_dict)
            else:
                # Checkpoint is directly the state_dict
                self.hybrik_model.load_state_dict(save_dict)
            
            self.hybrik_model.to(self.device)
            self.hybrik_model.eval()
            
            self._loaded = True
            logger.info(f"HybrIK model loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load HybrIK model: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
    
    def extract_frame(self, image: np.ndarray, prev_box: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Extract SMPL parameters from a single frame.
        
        Args:
            image: BGR image as numpy array (H, W, 3)
            prev_box: Previous bounding box for tracking
        
        Returns:
            Dict with SMPL parameters, or None if extraction fails
        """
        if not self._loaded:
            if not self.load_model():
                return None
        
        import cv2
        det_transform = T.Compose([T.ToTensor()])
        
        try:
            with torch.no_grad():
                # Convert BGR to RGB
                input_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Run person detection
                det_input = det_transform(input_image).to(self.device)
                det_output = self.det_model([det_input])[0]
                
                # Get bounding box
                if prev_box is None:
                    tight_bbox = get_one_box(det_output)
                else:
                    tight_bbox = get_max_iou_box(det_output, prev_box)
                
                if tight_bbox is None:
                    return None
                
                # Run HybrIK
                pose_input, bbox, img_center = self.transformation.test_transform(
                    input_image, tight_bbox
                )
                pose_input = pose_input.to(self.device)[None, :, :, :]
                
                pose_output = self.hybrik_model(
                    pose_input, 
                    flip_test=True,
                    bboxes=torch.from_numpy(np.array(bbox)).to(self.device).unsqueeze(0).float(),
                    img_center=torch.from_numpy(img_center).to(self.device).unsqueeze(0).float()
                )
                
                # Extract results
                # pred_theta_mats is (1, 24*9) - 24 joints, each with a 3x3 rotation matrix flattened
                smpl_pose_flat = pose_output.pred_theta_mats.cpu().numpy().squeeze()
                smpl_pose = smpl_pose_flat.reshape(24, 3, 3)  # Reshape to (24, 3, 3) rotation matrices
                
                result = {
                    "bbox": tight_bbox,
                    "smpl_pose": smpl_pose,  # (24, 3, 3) rotation matrices
                    "smpl_shape": pose_output.pred_shape.cpu().numpy().squeeze(),  # (10,) betas
                    "joints_3d_29": pose_output.pred_xyz_jts_29.cpu().numpy().reshape(-1, 3),  # (29, 3)
                    "joints_3d_24": pose_output.pred_xyz_jts_24_struct.cpu().numpy().reshape(24, 3),  # (24, 3)
                    "joints_3d_17": pose_output.pred_xyz_jts_17.cpu().numpy().reshape(17, 3),  # (17, 3) H36M format
                    "joints_2d_29": pose_output.pred_uvd_jts.cpu().numpy().reshape(-1, 3)[:, :2],  # (29, 2)
                    "pred_camera": pose_output.pred_camera.cpu().numpy().squeeze(),
                    "confidence": pose_output.maxvals.cpu().numpy()[:, :29].reshape(29),
                }
                
                return result
                
        except Exception as e:
            logger.warning(f"HybrIK extraction failed: {e}")
            return None
    
    def extract_video(
        self, 
        video_path: Path,
        max_frames: Optional[int] = None,
        progress_callback: Optional[callable] = None,
        frame_step: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract SMPL parameters from frames in a video.
        
        Args:
            video_path: Path to video file
            max_frames: Optional maximum frames to process
            progress_callback: Optional callback(current, total)
            frame_step: Process every Nth frame (1=all, 2=every other, etc.)
                       Higher values = faster but less temporal resolution
        """
        import cv2
        import os
        
        if not self._loaded:
            if not self.load_model():
                return []
        
        # Allow override via environment variable
        env_step = os.getenv("HYBRIK_FRAME_STEP")
        if env_step:
            try:
                frame_step = max(1, int(env_step))
            except ValueError:
                pass
        
        frames_data = []
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        if max_frames:
            total_frames = min(total_frames, max_frames)
        
        # Calculate frames to process with step
        frames_to_process = (total_frames + frame_step - 1) // frame_step
        
        prev_box = None
        frame_idx = 0
        processed_count = 0
        
        if frame_step > 1:
            logger.info(f"Processing {frames_to_process} frames (every {frame_step}th) from {video_path}")
        else:
            logger.info(f"Processing {total_frames} frames from {video_path}")
        
        while True:
            ret, frame = cap.read()
            if not ret or (max_frames and frame_idx >= max_frames):
                break
            
            # Only process every Nth frame
            if frame_idx % frame_step == 0:
                result = self.extract_frame(frame, prev_box)
                if result:
                    result["frame_idx"] = frame_idx
                    result["timestamp"] = frame_idx / fps if fps > 0 else 0
                    frames_data.append(result)
                    prev_box = result["bbox"]
                
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, frames_to_process)
            
            frame_idx += 1
        
        cap.release()
        logger.info(f"Extracted {len(frames_data)} frames with SMPL parameters")
        return frames_data


def smpl_to_mediapipe_format(smpl_frame: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert SMPL output to MediaPipe-like format for compatibility
    with existing metric calculations.
    """
    joints_3d = smpl_frame.get("joints_3d_24")  # Use 24-joint SMPL format
    joints_2d = smpl_frame.get("joints_2d_29")
    
    if joints_3d is None:
        return {"landmarks": [], "landmarks_3d": []}
    
    # Create 33-element landmarks list (MediaPipe format)
    landmarks = [{"x": 0, "y": 0, "z": 0, "visibility": 0} for _ in range(33)]
    landmarks_3d = [{"x": 0, "y": 0, "z": 0, "visibility": 0} for _ in range(33)]
    
    # Map SMPL joints to MediaPipe indices
    for smpl_idx, mp_idx in SMPL_TO_MEDIAPIPE.items():
        if smpl_idx < len(joints_3d):
            joint_3d = joints_3d[smpl_idx]
            landmarks_3d[mp_idx] = {
                "x": float(joint_3d[0]),
                "y": float(joint_3d[1]),
                "z": float(joint_3d[2]),
                "visibility": 1.0,
            }
            
            if joints_2d is not None and smpl_idx < len(joints_2d):
                joint_2d = joints_2d[smpl_idx]
                landmarks[mp_idx] = {
                    "x": float(joint_2d[0]),
                    "y": float(joint_2d[1]),
                    "z": float(joint_3d[2]),
                    "visibility": 1.0,
                }
    
    return {
        "landmarks": landmarks,
        "landmarks_3d": landmarks_3d,
        "smpl_pose": smpl_frame.get("smpl_pose"),
        "smpl_shape": smpl_frame.get("smpl_shape"),
        "frame_idx": smpl_frame.get("frame_idx", 0),
        "timestamp": smpl_frame.get("timestamp", 0),
    }


def detect_key_frames_smpl(smpl_frames: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Detect Address, Top, and Impact frames from SMPL joint data.
    
    Uses the 3D wrist positions to identify key swing phases:
    - Address: First frame (setup position)
    - Top: First significant peak where hands are highest (minimum wrist Y in SMPL coords)
    - Impact: When hands reach lowest point after top (maximum wrist Y after top)
    
    Key insight: The algorithm must find the FIRST backswing peak, not the global minimum,
    because the follow-through high point may be higher than the backswing top.
    
    Returns:
        Dict with "address_idx", "top_idx", "impact_idx"
    """
    from scipy.signal import find_peaks, savgol_filter
    
    if not smpl_frames:
        return {"address_idx": 0, "top_idx": 0, "impact_idx": 0}
    
    # Extract wrist Y values (average of left and right)
    l_wrist_idx = SMPL_JOINTS["l_wrist"]
    r_wrist_idx = SMPL_JOINTS["r_wrist"]
    
    wrist_y = []
    for f in smpl_frames:
        joints = f.get("joints_3d_24")
        if joints is not None and len(joints) > max(l_wrist_idx, r_wrist_idx):
            avg_y = (joints[l_wrist_idx][1] + joints[r_wrist_idx][1]) / 2
            wrist_y.append(avg_y)
        else:
            wrist_y.append(0)
    
    wrist_y = np.array(wrist_y)
    
    # Apply smoothing to remove jitter (crucial for stability)
    if len(wrist_y) >= 5:
        window_length = min(11, len(wrist_y) if len(wrist_y) % 2 == 1 else len(wrist_y) - 1)
        if window_length >= 5:
            wrist_y = savgol_filter(wrist_y, window_length=window_length, polyorder=2)
            
    n_frames = len(wrist_y)
    
    # Calculate velocity
    velocity = np.gradient(wrist_y)
    
    # Address = first frame (or first stable position)
    address_idx = 0
    address_y = wrist_y[address_idx]
    
    # Top = first significant local minimum (hands highest)
    # Strategy: Find velocity zero-crossings from negative to positive (upward to downward)
    # In SMPL coords: negative Y velocity = hands going up, positive = hands going down
    
    top_idx = 0
    local_minima = []
    
    # Find local minima using velocity sign changes
    for i in range(5, n_frames - 5):
        # Look for velocity zero-crossing from negative to positive
        # (hands stop going up and start going down)
        if velocity[i-1] <= 0 and velocity[i] > 0:
            # Confirm it's a real peak by checking surrounding values
            if wrist_y[i] < wrist_y[max(0, i-5)] and wrist_y[i] < wrist_y[min(n_frames-1, i+5)]:
                local_minima.append(i)
    
    # Find the first significant local minimum
    # (hands must have risen meaningfully from the start position)
    start_y = wrist_y[0] if len(wrist_y) > 0 else 0
    
    # Determine threshold based on Y range (SMPL coords are in meters)
    y_range = np.max(wrist_y) - np.min(wrist_y)
    threshold = max(0.05, y_range * 0.15)  # At least 15% of range or 5cm
    
    for min_idx in local_minima:
        # Check if this is a significant backswing
        if start_y - wrist_y[min_idx] > threshold:
            top_idx = min_idx
            break
    
    # Fallback: use scipy find_peaks on first 60% of video
    if top_idx == 0:
        search_end = int(n_frames * 0.6)
        first_part_y = wrist_y[:search_end] if search_end > 10 else wrist_y
        
        # Try with adaptive prominence
        y_std = np.std(first_part_y)
        prominence = max(0.02, y_std * 0.5)
        
        peaks, _ = find_peaks(-first_part_y, distance=5, prominence=prominence)
        if len(peaks) > 0:
            top_idx = peaks[0]
        else:
            # Last resort: simple argmin in first 60%
            top_idx = int(np.argmin(first_part_y))
    
    # Impact = when hands reach their lowest point after top
    # In SMPL coords: positive Y = down, so max Y after top is impact
    
    impact_search_start = top_idx + 1
    max_downswing_frames = 25  # ~0.8s at 30fps (allows for slower swings)
    search_end = min(impact_search_start + max_downswing_frames, n_frames)
    
    impact_idx = n_frames - 1  # Default
    
    if impact_search_start < search_end:
        # Find where Y velocity crosses from positive to negative
        # (hands transition from going down to going up in follow-through)
        for i in range(impact_search_start + 1, search_end):
            if velocity[i-1] > 0 and velocity[i] <= 0:
                # Found the velocity zero-crossing
                # Pick the frame with velocity closest to zero
                if abs(velocity[i-1]) < abs(velocity[i]):
                    impact_idx = i - 1
                else:
                    impact_idx = i
                break
        else:
            # Fallback: find the maximum Y (hands lowest) in search range
            post_top_y = wrist_y[impact_search_start:search_end]
            impact_idx = impact_search_start + int(np.argmax(post_top_y))
    
    # Ensure chronological order
    if top_idx <= address_idx:
        top_idx = address_idx + 5
    if impact_idx <= top_idx:
        impact_idx = min(top_idx + 10, n_frames - 1)
    
    return {
        "address_idx": address_idx,
        "top_idx": top_idx,
        "impact_idx": impact_idx,
    }


# Singleton instance for reuse
_hybrik_extractor: Optional[HybrIKExtractor] = None

def get_hybrik_extractor() -> Optional[HybrIKExtractor]:
    """Get or create the HybrIK extractor singleton."""
    global _hybrik_extractor
    if _hybrik_extractor is None and HYBRIK_AVAILABLE:
        _hybrik_extractor = HybrIKExtractor()
    return _hybrik_extractor


def is_smpl_available() -> bool:
    """Check if SMPL/HybrIK is available."""
    return HYBRIK_AVAILABLE



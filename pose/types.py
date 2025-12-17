from typing import List, Optional, NamedTuple

class Point3D(NamedTuple):
    x: float
    y: float
    z: float
    visibility: float

class FramePose(NamedTuple):
    frame_index: int
    timestamp_ms: float
    landmarks: List[Point3D]
    smpl_pose: Optional[List[List[List[float]]]] = None  # 24x3x3 rotation matrices
    smpl_joints: Optional[List[List[float]]] = None
    smpl_joints_2d: Optional[List[List[float]]] = None
    smpl_camera: Optional[float] = None
    smpl_bbox: Optional[List[float]] = None

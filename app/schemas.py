from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    handicap: Optional[float] = None
    skill_level: Optional[str] = "Beginner"
    handedness: Optional[str] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    handicap: Optional[float] = None
    handedness: Optional[str] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Swing Schemas ---
class SwingAnalysisRequest(BaseModel):
    handedness: str  # "right" or "left"
    view: str        # "face_on" or "down_the_line"
    club_type: str   # "driver", "iron", "wedge"

class SwingPhases(BaseModel):
    address_frame: int
    top_frame: int
    impact_frame: int
    finish_frame: int

class SwingMetrics(BaseModel):
    # Core 10 metrics (HybrIK-based)
    tempo_ratio: Optional[float] = None
    backswing_duration_ms: Optional[float] = None
    downswing_duration_ms: Optional[float] = None
    
    # Chest Turn (renamed from shoulder_turn for clarity)
    chest_turn_top_deg: Optional[float] = None
    
    # Pelvis Turn (renamed from hip_turn for clarity)
    pelvis_turn_top_deg: Optional[float] = None
    
    # X-Factor (chest - pelvis separation at top)
    x_factor_top_deg: Optional[float] = None
    
    # Spine Angle (forward bend)
    spine_angle_address_deg: Optional[float] = None
    spine_angle_impact_deg: Optional[float] = None
    
    # Lead Arm (elbow angle - 180° = straight)
    lead_arm_address_deg: Optional[float] = None
    lead_arm_top_deg: Optional[float] = None
    lead_arm_impact_deg: Optional[float] = None
    
    # Trail Elbow (elbow angle)
    trail_elbow_address_deg: Optional[float] = None
    trail_elbow_top_deg: Optional[float] = None
    trail_elbow_impact_deg: Optional[float] = None
    
    # Knee Flex (at address)
    knee_flex_left_address_deg: Optional[float] = None
    knee_flex_right_address_deg: Optional[float] = None
    
    # Head Sway (lateral movement range)
    head_sway_range: Optional[float] = None
    
    # Early Extension (hip movement toward ball)
    early_extension_amount: Optional[float] = None
    
    # Swing Path (negative = shallow/inside, positive = over-the-top/outside)
    swing_path_index: Optional[float] = None

    # Hand Position (DTL)
    hand_height_at_top_index: Optional[float] = None
    hand_width_at_top_index: Optional[float] = None
    head_drop_cm: Optional[float] = None
    head_rise_cm: Optional[float] = None
    
    # Extended MHR metrics (finish, sway, plane)
    finish_balance: Optional[float] = None
    chest_turn_finish_deg: Optional[float] = None
    pelvis_turn_finish_deg: Optional[float] = None
    spine_angle_top_deg: Optional[float] = None
    spine_angle_finish_deg: Optional[float] = None
    extension_from_address_deg: Optional[float] = None
    head_rise_top_to_finish_cm: Optional[float] = None
    head_lateral_shift_address_to_finish_cm: Optional[float] = None
    hand_height_finish_norm: Optional[float] = None
    hand_depth_finish_norm: Optional[float] = None
    hand_height_finish_label: Optional[str] = None
    hand_depth_finish_label: Optional[str] = None
    pelvis_sway_top_cm: Optional[float] = None
    pelvis_sway_impact_cm: Optional[float] = None
    pelvis_sway_finish_cm: Optional[float] = None
    pelvis_sway_range_cm: Optional[float] = None
    shoulder_sway_top_cm: Optional[float] = None
    shoulder_sway_impact_cm: Optional[float] = None
    shoulder_sway_finish_cm: Optional[float] = None
    shoulder_sway_range_cm: Optional[float] = None
    swing_plane_top_deg: Optional[float] = None
    swing_plane_impact_deg: Optional[float] = None
    swing_plane_deviation_top_deg: Optional[float] = None
    swing_plane_deviation_impact_deg: Optional[float] = None
    swing_plane_shift_top_to_impact_deg: Optional[float] = None
    arm_above_plane_at_top: Optional[bool] = None
    
    # Backward compatibility fields (deprecated, kept for old sessions)
    shoulder_turn_top_deg: Optional[float] = None
    hip_turn_top_deg: Optional[float] = None
    spine_tilt_address_deg: Optional[float] = None
    spine_tilt_impact_deg: Optional[float] = None
    head_movement_forward_cm: Optional[float] = None
    head_movement_vertical_cm: Optional[float] = None
    shaft_lean_impact_deg: Optional[float] = None
    lead_wrist_flexion_address_deg: Optional[float] = None
    lead_wrist_flexion_top_deg: Optional[float] = None
    lead_wrist_flexion_impact_deg: Optional[float] = None
    lead_wrist_hinge_top_deg: Optional[float] = None

class MetricScore(BaseModel):
    value: float
    score: str # "green", "yellow", "red"
class MetricScore(BaseModel):
    value: float
    score: str # "green", "yellow", "red"
    target_min: Optional[float] = None
    target_max: Optional[float] = None
    weight: float = 1.0

class SwingScores(BaseModel):
    overall_score: int
    metric_scores: Dict[str, MetricScore]

# --- Drill Schemas ---
class DrillBase(BaseModel):
    title: str
    description: str
    category: str
    difficulty: str = "Beginner"
    video_url: Optional[str] = None
    target_metric: Optional[str] = None

class DrillCreate(DrillBase):
    pass

class DrillResponse(DrillBase):
    id: str

    class Config:
        from_attributes = True


class SwingFeedback(BaseModel):
    summary: str
    priority_issues: List[str]
    drills: List[DrillResponse]
    phase_feedback: Optional[Dict[str, str]] = {}

class SimpleScores(BaseModel):
    overall_score: int

class SessionSummaryResponse(BaseModel):
    session_id: str
    scores: SimpleScores
    metadata: SwingAnalysisRequest
    is_personal_best: bool = False
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AnalysisResponse(BaseModel):
    session_id: Optional[str] = None
    video_url: Optional[str] = None
    is_personal_best: bool = False
    phases: SwingPhases
    metrics: SwingMetrics
    scores: SwingScores
    feedback: SwingFeedback
    metadata: SwingAnalysisRequest
    created_at: Optional[datetime] = None

class ReferenceProfileCreate(BaseModel):
    name: str
    metrics: SwingMetrics # We use the metrics from a session to build targets

class ReferenceProfileResponse(BaseModel):
    id: str
    name: str
    is_default: bool

class DashboardStats(BaseModel):
    total_sessions: int
    average_score: float
    last_session_date: Optional[datetime] = None
    personal_bests: Dict[str, Optional[int]] # club_type -> score

class TrendPoint(BaseModel):
    date: datetime
    score: int
    metrics: Dict[str, float] # metric_name -> value

class TrendResponse(BaseModel):
    club_type: str
    data: List[TrendPoint]

class MetricDiff(BaseModel):
    metric_name: str
    session_1_value: float
    session_2_value: float
    diff: float # session_2 - session_1
    improvement: bool # True if session_2 is better (depends on metric)

class ComparisonResponse(BaseModel):
    session_1: AnalysisResponse
    session_2: AnalysisResponse
    metrics: List[MetricDiff]


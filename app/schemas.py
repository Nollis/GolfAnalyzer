from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    handicap: Optional[float] = None
    skill_level: Optional[str] = "Beginner"
    handedness: Optional[str] = None

class UserCreate(UserBase):
    password: str

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
    tempo_ratio: float
    backswing_duration_ms: float
    downswing_duration_ms: float
    
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
    target_min: Optional[float] = None
    target_max: Optional[float] = None

class SwingScores(BaseModel):
    overall_score: int
    metric_scores: Dict[str, MetricScore]

class Drill(BaseModel):
    title: str
    description: str

class SwingFeedback(BaseModel):
    summary: str
    priority_issues: List[str]
    drills: List[Drill]

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


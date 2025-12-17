from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class SwingSession(Base):
    __tablename__ = "swing_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    handedness = Column(String)
    view = Column(String)
    club_type = Column(String)
    video_url = Column(String, nullable=True) # Path or URL
    
    # Scores
    overall_score = Column(Integer)
    is_personal_best = Column(Boolean, default=False)
    
    # User Link
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Nullable for now to support migration/dev
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    metrics = relationship("SwingMetric", back_populates="session", uselist=False)
    phases = relationship("SwingPhase", back_populates="session", uselist=False)
    feedback = relationship("SwingFeedbackDB", back_populates="session", uselist=False)

class SwingMetric(Base):
    __tablename__ = "swing_metrics"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("swing_sessions.id"))
    
    tempo_ratio = Column(Float)
    backswing_duration_ms = Column(Float)
    downswing_duration_ms = Column(Float)
    
    # New Metrics (matching schema)
    chest_turn_top_deg = Column(Float)
    pelvis_turn_top_deg = Column(Float)
    x_factor_top_deg = Column(Float)
    spine_angle_address_deg = Column(Float)
    spine_angle_impact_deg = Column(Float)
    lead_arm_address_deg = Column(Float)
    lead_arm_top_deg = Column(Float)
    lead_arm_impact_deg = Column(Float)
    trail_elbow_address_deg = Column(Float)
    trail_elbow_top_deg = Column(Float)
    trail_elbow_impact_deg = Column(Float)
    knee_flex_left_address_deg = Column(Float)
    knee_flex_right_address_deg = Column(Float)
    head_sway_range = Column(Float)
    early_extension_amount = Column(Float)
    early_extension_amount = Column(Float, nullable=True)
    
    # Swing Path
    swing_path_index = Column(Float, nullable=True)

    # Hand Position (DTL)
    hand_height_at_top_index = Column(Float, nullable=True)
    hand_width_at_top_index = Column(Float, nullable=True)
    head_drop_cm = Column(Float, nullable=True)
    head_rise_cm = Column(Float, nullable=True)

    # Extended MHR Metrics (Finish, Sway, Plane)
    finish_balance = Column(Float, nullable=True)
    
    # Sway
    pelvis_sway_top_cm = Column(Float, nullable=True)
    pelvis_sway_impact_cm = Column(Float, nullable=True)
    pelvis_sway_finish_cm = Column(Float, nullable=True)
    shoulder_sway_top_cm = Column(Float, nullable=True)
    shoulder_sway_impact_cm = Column(Float, nullable=True)
    shoulder_sway_finish_cm = Column(Float, nullable=True)
    pelvis_sway_range_cm = Column(Float, nullable=True)
    shoulder_sway_range_cm = Column(Float, nullable=True)

    # Swing Plane
    swing_plane_top_deg = Column(Float, nullable=True)
    swing_plane_impact_deg = Column(Float, nullable=True)
    swing_plane_deviation_top_deg = Column(Float, nullable=True)
    swing_plane_deviation_impact_deg = Column(Float, nullable=True)
    swing_plane_shift_top_to_impact_deg = Column(Float, nullable=True)
    arm_above_plane_at_top = Column(Boolean, nullable=True)

    # Finish & Head Recovery
    spine_angle_finish_deg = Column(Float, nullable=True)
    spine_angle_top_deg = Column(Float, nullable=True) # Also used for extension calc
    extension_from_address_deg = Column(Float, nullable=True)
    chest_turn_finish_deg = Column(Float, nullable=True)
    pelvis_turn_finish_deg = Column(Float, nullable=True)
    head_rise_top_to_finish_cm = Column(Float, nullable=True)
    head_lateral_shift_address_to_finish_cm = Column(Float, nullable=True)
    
    # Hand Finish
    hand_height_finish_norm = Column(Float, nullable=True)
    hand_depth_finish_norm = Column(Float, nullable=True)
    hand_height_finish_label = Column(String, nullable=True)
    hand_depth_finish_label = Column(String, nullable=True)
    
    # Backward compatibility fields
    # Legacy Metrics (kept for backward compatibility)
    shoulder_turn_top_deg = Column(Float, nullable=True)
    hip_turn_top_deg = Column(Float, nullable=True)
    spine_tilt_address_deg = Column(Float, nullable=True)
    spine_tilt_impact_deg = Column(Float, nullable=True)
    head_movement_forward_cm = Column(Float, nullable=True)
    head_movement_vertical_cm = Column(Float, nullable=True)
    shaft_lean_impact_deg = Column(Float, nullable=True)
    
    # Wrist angles
    lead_wrist_flexion_address_deg = Column(Float, nullable=True)
    lead_wrist_flexion_top_deg = Column(Float, nullable=True)
    lead_wrist_flexion_impact_deg = Column(Float, nullable=True)
    lead_wrist_hinge_top_deg = Column(Float, nullable=True)

    session = relationship("SwingSession", back_populates="metrics")

class SwingPhase(Base):
    __tablename__ = "swing_phases"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("swing_sessions.id"))
    
    address_frame = Column(Integer)
    top_frame = Column(Integer)
    impact_frame = Column(Integer)
    finish_frame = Column(Integer)

    session = relationship("SwingSession", back_populates="phases")

class SwingFeedbackDB(Base):
    __tablename__ = "swing_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("swing_sessions.id"))
    
    summary = Column(String)
    priority_issues = Column(JSON) # List of strings
    drills = Column(JSON) # List of dicts
    phase_feedback = Column(JSON) # Dict of phase -> feedback string

    session = relationship("SwingSession", back_populates="feedback")

class ReferenceProfileDB(Base):
    __tablename__ = "reference_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True)
    targets = Column(JSON) # Dict of metric targets
    is_default = Column(Integer, default=0) # 0 or 1 (boolean)

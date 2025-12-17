from typing import Dict, NamedTuple, Optional

class MetricTarget(NamedTuple):
    target: float
    inner_tol: float
    outer_tol: float
    weight: float = 1.0 
    
    # For backward compatibility with UI that expects min_val/max_val
    # We'll treat [target-inner, target+inner] as the "ideal" range (Green)
    @property
    def min_val(self) -> float:
        return self.target - self.inner_tol
        
    @property
    def max_val(self) -> float:
        return self.target + self.inner_tol
        
    @property
    def ideal_val(self) -> float:
        return self.target

class ReferenceProfile:
    def __init__(self, name: str, view: str, club_type: str, targets: Dict[str, MetricTarget]):
        self.name = name
        self.view = view
        self.club_type = club_type
        self.targets = targets

def get_dtl_targets() -> Dict[str, MetricTarget]:
    """
    Targets for Down-The-Line view.
    Updated for accurate 3D MHR measurements.
    Widened tolerances for recreational golfers.
    """
    return {
        # Tempo (Universal) - widened for recreational
        "tempo_ratio": MetricTarget(3.0, 0.3, 1.0, 1.0),
        "backswing_duration_ms": MetricTarget(750, 200, 500, 0.5),
        "downswing_duration_ms": MetricTarget(250, 50, 150, 0.5),
        
        # Rotational (3D MHR - accurate values)
        "chest_turn_top_deg": MetricTarget(85.0, 15.0, 35.0, 0.8),
        "pelvis_turn_top_deg": MetricTarget(35.0, 15.0, 30.0, 0.8),
        "x_factor_top_deg": MetricTarget(50.0, 20.0, 40.0, 1.0),
        
        # Spine Angle (forward bend from vertical)
        "spine_angle_address_deg": MetricTarget(35.0, 15.0, 30.0, 0.8),
        "spine_angle_impact_deg": MetricTarget(35.0, 15.0, 30.0, 0.8),
        
        # Arms - widened significantly for 3D variation
        "lead_arm_address_deg": MetricTarget(170.0, 15.0, 40.0, 0.7),
        "lead_arm_top_deg": MetricTarget(160.0, 25.0, 60.0, 0.8),
        "lead_arm_impact_deg": MetricTarget(150.0, 30.0, 70.0, 0.0),
        
        "trail_elbow_address_deg": MetricTarget(155.0, 20.0, 50.0, 0.6),
        "trail_elbow_top_deg": MetricTarget(100.0, 30.0, 60.0, 1.0),
        "trail_elbow_impact_deg": MetricTarget(150.0, 25.0, 60.0, 0.8),
        
        # Legs - widened
        "knee_flex_left_address_deg": MetricTarget(160.0, 15.0, 35.0, 0.7),
        "knee_flex_right_address_deg": MetricTarget(160.0, 15.0, 35.0, 0.7),
        
        # Stability - Head Sway in cm (widened for recreational)
        "head_sway_range": MetricTarget(4.0, 4.0, 10.0, 1.0),
        "early_extension_amount": MetricTarget(0.0, 0.03, 0.08, 1.0),
        
        # Head Vertical (cm) - widened
        "head_drop_cm": MetricTarget(3.0, 5.0, 12.0, 0.8),
        "head_rise_cm": MetricTarget(3.0, 5.0, 15.0, 0.8),
        
        # Swing Path - widened
        "swing_path_index": MetricTarget(-0.2, 0.3, 0.6, 1.0),
        
        # Hand Position
        "hand_height_at_top_index": MetricTarget(0.2, 0.2, 0.4, 0.8),
        "hand_width_at_top_index": MetricTarget(1.2, 0.4, 0.7, 0.8),
        
        # Backward compat keys
        "shoulder_turn_top_deg": MetricTarget(85.0, 15.0, 35.0, 0.8),
        "hip_turn_top_deg": MetricTarget(35.0, 15.0, 30.0, 0.8),
        "spine_tilt_address_deg": MetricTarget(35.0, 15.0, 30.0, 0.8),
        "spine_tilt_impact_deg": MetricTarget(35.0, 15.0, 30.0, 0.8),
    }

def get_face_on_targets() -> Dict[str, MetricTarget]:
    """
    Targets for Face-On view.
    Updated for accurate 3D MHR measurements.
    """
    return {
        # Tempo
        "tempo_ratio": MetricTarget(3.0, 0.3, 1.2, 1.0),
        "backswing_duration_ms": MetricTarget(750, 150, 300, 0.5),
        "downswing_duration_ms": MetricTarget(250, 50, 100, 0.5),
        
        # Rotational (3D MHR - accurate values)
        "chest_turn_top_deg": MetricTarget(90.0, 10.0, 20.0, 0.8),
        "pelvis_turn_top_deg": MetricTarget(45.0, 10.0, 20.0, 0.8),
        "x_factor_top_deg": MetricTarget(45.0, 15.0, 25.0, 1.0),
        
        # Spine Angle (forward bend from vertical, 3D)
        "spine_angle_address_deg": MetricTarget(35.0, 10.0, 20.0, 1.0),
        "spine_angle_impact_deg": MetricTarget(35.0, 10.0, 20.0, 1.0),
        
        # Arms
        "lead_arm_address_deg": MetricTarget(175.0, 5.0, 20.0, 0.7),
        "lead_arm_top_deg": MetricTarget(170.0, 10.0, 20.0, 0.8),
        "lead_arm_impact_deg": MetricTarget(170.0, 10.0, 30.0, 1.0),
        
        "trail_elbow_address_deg": MetricTarget(160.0, 10.0, 20.0, 0.6),
        "trail_elbow_top_deg": MetricTarget(90.0, 15.0, 30.0, 1.0),
        "trail_elbow_impact_deg": MetricTarget(160.0, 10.0, 20.0, 0.8),
        
        # Legs
        "knee_flex_left_address_deg": MetricTarget(155.0, 10.0, 25.0, 1.0),
        "knee_flex_right_address_deg": MetricTarget(155.0, 10.0, 25.0, 1.0),
        
        # Stability - Head Sway in cm (3D)
        "head_sway_range": MetricTarget(3.0, 2.0, 5.0, 1.2),
        "early_extension_amount": MetricTarget(0.0, 0.02, 0.05, 1.2),
        
        # Head Vertical (cm)
        "head_drop_cm": MetricTarget(2.0, 3.0, 6.0, 1.0),
        "head_rise_cm": MetricTarget(1.0, 2.0, 5.0, 1.3),
        
        # Hand Position
        "hand_height_at_top_index": MetricTarget(0.2, 0.15, 0.3, 1.0),
        "hand_width_at_top_index": MetricTarget(1.2, 0.3, 0.5, 1.0),
        
        # Swing Path
        "swing_path_index": MetricTarget(-0.3, 0.2, 0.5, 1.0),
        
        # Backward compat
        "shoulder_turn_top_deg": MetricTarget(90.0, 10.0, 20.0, 0.8),
        "hip_turn_top_deg": MetricTarget(45.0, 10.0, 20.0, 0.8),
        "spine_tilt_address_deg": MetricTarget(35.0, 10.0, 20.0, 1.0),
        "spine_tilt_impact_deg": MetricTarget(35.0, 10.0, 20.0, 1.0),
    }

def get_default_profile() -> ReferenceProfile:
    # Default to DTL as it's safer/more common for casual users
    return ReferenceProfile("Default Pro (DTL)", "dtl", "driver", get_dtl_targets())

def get_reference_profile_for(club_type: str, view: str, skill_level: str = "pro") -> ReferenceProfile:
    view = view.lower() if view else "dtl"
    
    if view in ["face_on", "faceon", "front"]:
        targets = get_face_on_targets()
        name = f"Pro {club_type.title()} (Face-On)"
        view_normalized = "face_on"
    else:
        targets = get_dtl_targets()
        name = f"Pro {club_type.title()} (DTL)"
        view_normalized = "dtl"
        
    return ReferenceProfile(name, view_normalized, club_type, targets)

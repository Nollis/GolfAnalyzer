from typing import Dict, NamedTuple, Optional

class MetricTarget(NamedTuple):
    min_val: float
    max_val: float
    ideal_val: float
    weight: float # Importance 0-1

class ReferenceProfile:
    def __init__(self, name: str, targets: Dict[str, MetricTarget]):
        self.name = name
        self.targets = targets

def get_default_profile() -> ReferenceProfile:
    # Based on general pro averages - updated for 10 core metrics
    targets = {
        # Tempo
        "tempo_ratio": MetricTarget(2.5, 3.5, 3.0, 1.0),
        "backswing_duration_ms": MetricTarget(600, 1000, 750, 0.5),
        "downswing_duration_ms": MetricTarget(200, 350, 250, 0.5),
        
        # Chest Turn (renamed from shoulder_turn)
        "chest_turn_top_deg": MetricTarget(80, 110, 90, 0.8),
        "shoulder_turn_top_deg": MetricTarget(80, 110, 90, 0.8),  # Backward compat
        
        # Pelvis Turn (renamed from hip_turn)
        "pelvis_turn_top_deg": MetricTarget(35, 55, 45, 0.7),
        "hip_turn_top_deg": MetricTarget(35, 55, 45, 0.7),  # Backward compat
        
        # X-Factor
        "x_factor_top_deg": MetricTarget(30, 55, 40, 0.9),
        
        # Spine Angle (renamed from spine_tilt)
        "spine_angle_address_deg": MetricTarget(25, 45, 35, 0.8),
        "spine_angle_impact_deg": MetricTarget(25, 45, 35, 0.8),
        "spine_tilt_address_deg": MetricTarget(25, 45, 35, 0.8),  # Backward compat
        "spine_tilt_impact_deg": MetricTarget(25, 45, 35, 0.8),  # Backward compat
        
        # Lead Arm (elbow angle, 180° = straight)
        "lead_arm_address_deg": MetricTarget(160, 180, 175, 0.7),
        "lead_arm_top_deg": MetricTarget(160, 180, 175, 0.8),
        "lead_arm_impact_deg": MetricTarget(160, 180, 175, 0.9),
        
        # Trail Elbow
        "trail_elbow_address_deg": MetricTarget(150, 170, 160, 0.6),
        "trail_elbow_top_deg": MetricTarget(75, 105, 90, 0.9),  # ~90° at top
        "trail_elbow_impact_deg": MetricTarget(150, 170, 160, 0.8),
        
        # Knee Flex (at address)
        "knee_flex_left_address_deg": MetricTarget(130, 165, 150, 0.7),
        "knee_flex_right_address_deg": MetricTarget(130, 165, 150, 0.7),
        
        # Head Sway (range - minimal is better)
        "head_sway_range": MetricTarget(0, 0.05, 0.02, 0.8),  # Normalized coords
        
        # Early Extension (amount - less is better)
        "early_extension_amount": MetricTarget(-0.02, 0.02, 0, 0.9),  # Normalized coords
    }
    return ReferenceProfile("Default Pro", targets)

def get_reference_profile_for(club_type: str, view: str, skill_level: str = "pro") -> ReferenceProfile:
    # In a real app, this would return different profiles based on inputs.
    # For now, return the default.
    return get_default_profile()

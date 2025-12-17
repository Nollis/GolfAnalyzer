from typing import Dict, Optional
from app.schemas import SwingMetrics, SwingScores, MetricScore
from reference.reference_profiles import ReferenceProfile, MetricTarget

# View-specific weights
# With 3D MHR, rotational metrics are now accurate from any view
DTL_WEIGHTS = {
    "tempo_ratio": 1.5,
    "backswing_duration_ms": 0.0, # Info only (Tempo covers it)
    "downswing_duration_ms": 0.0, # Info only
    "chest_turn_top_deg": 0.8,   # Now enabled with 3D MHR
    "pelvis_turn_top_deg": 0.8,  # Now enabled with 3D MHR
    "x_factor_top_deg": 1.0,     # Now enabled with 3D MHR
    "spine_angle_address_deg": 0.8,
    "spine_angle_impact_deg": 0.8,
    "lead_arm_address_deg": 0.7,
    "lead_arm_top_deg": 0.8,
    "lead_arm_impact_deg": 0.0, # Informational
    "trail_elbow_address_deg": 0.6,
    "trail_elbow_top_deg": 1.0,
    "trail_elbow_impact_deg": 0.8,
    "knee_flex_left_address_deg": 0.7,
    "knee_flex_right_address_deg": 0.7,
    "head_sway_range": 1.0,
    "early_extension_amount": 1.2,
    "swing_path_index": 1.0,
    "hand_height_at_top_index": 1.0,
    "hand_width_at_top_index": 1.0,
    "head_drop_cm": 1.0,
    "head_rise_cm": 1.2,
}

FACE_ON_WEIGHTS = {
    "tempo_ratio": 1.5,
    "chest_turn_top_deg": 0.8,
    "pelvis_turn_top_deg": 0.8,
    "x_factor_top_deg": 1.0,
    "spine_angle_address_deg": 1.3,
    "spine_angle_impact_deg": 1.3,
    "lead_arm_impact_deg": 1.3,
    "trail_elbow_top_deg": 1.3,
    "knee_flex_left_address_deg": 1.0,
    "knee_flex_right_address_deg": 1.0,
    "head_sway_range": 1.4,
    "early_extension_amount": 1.4,
    # Exclude DTL specific
    "swing_path_index": 0.0,
    "hand_height_at_top_index": 0.0,
    "hand_width_at_top_index": 0.0,
    "head_drop_cm": 1.2,
    "head_rise_cm": 1.2,
}

def calculate_smooth_score(value: float, target: float, inner_tol: float, outer_tol: float) -> float:
    """
    Calculate a smooth 0-100 score.
    100 if within target +/- inner_tol.
    Linearly drops to 0 at target +/- outer_tol.
    """
    diff = abs(value - target)
    
    if diff <= inner_tol:
        return 100.0
    
    if diff >= outer_tol:
        return 0.0
    
    # Linear interpolation between inner_tol (100) and outer_tol (0)
    # score = 100 * (1 - (diff - inner_tol) / (outer_tol - inner_tol))
    span = outer_tol - inner_tol
    if span <= 0: return 0.0
    
    return 100.0 * (1.0 - (diff - inner_tol) / span)

class Scorer:
    def build_scores(self, metrics: SwingMetrics, ref: ReferenceProfile) -> SwingScores:
        metric_scores: Dict[str, MetricScore] = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        metrics_dict = metrics.dict()
        
        # Select weight map
        weight_map = FACE_ON_WEIGHTS if ref.view == "face_on" else DTL_WEIGHTS

        for key, target in ref.targets.items():
            val = metrics_dict.get(key)
            
            # Skip missing values (don't penalize)
            if val is None:
                continue
                
            # Calculate smooth score
            numeric_score = calculate_smooth_score(
                val, 
                target.target, 
                target.inner_tol, 
                target.outer_tol
            )
            
            # Determine Color based on numeric score
            # Widened thresholds for more yellows
            if numeric_score >= 70:
                score_str = "green"
            elif numeric_score >= 40:
                score_str = "yellow"
            else:
                score_str = "red"
                
            # Determine Weight
            # Use view-specific weight if available, else default from target
            weight = weight_map.get(key, target.weight)
            
            # Confidence handling (if we had it, for now assume 1.0)
            # effective_weight = weight * confidence
            
            metric_scores[key] = MetricScore(
                value=val,
                score=score_str,
                target_min=target.min_val,
                target_max=target.max_val,
                weight=weight
            )
            
            # Only add to total if weight > 0
            if weight > 0:
                total_weighted_score += numeric_score * weight
                total_weight += weight
        
        overall_score = 0
        if total_weight > 0:
            overall_score = int(total_weighted_score / total_weight)

        return SwingScores(
            overall_score=overall_score,
            metric_scores=metric_scores
        )

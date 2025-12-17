"""
Improvement Delta - Compare current swing to recent swings for trend analysis.

Computes per-metric deltas vs last swing, vs average, and consistency stats.
"""

import numpy as np
from typing import Dict, Any, List, Optional


# Key metrics to track for improvement analysis
KEY_METRICS = [
    "x_factor_top_deg",
    "chest_turn_top_deg",
    "pelvis_turn_top_deg",
    "lead_arm_top_deg",
    "trail_elbow_top_deg",
    "spine_angle_address_deg",
    "head_sway_range",
    "head_drop_cm",
    "head_rise_cm",
    "knee_flex_left_address_deg",
    "finish_balance",
    "pelvis_sway_impact_cm",
    "shoulder_sway_impact_cm",
    "swing_plane_deviation_top_deg",
]


def compute_metric_delta(
    current_value: Optional[float],
    recent_values: List[Optional[float]]
) -> Dict[str, Optional[float]]:
    """
    Compute delta statistics for a single metric.
    
    Args:
        current_value: Current swing's metric value
        recent_values: List of previous values (newest first)
    
    Returns:
        Dict with delta_vs_last, delta_vs_mean, consistency_std
    """
    result = {
        "delta_vs_last": None,
        "delta_vs_mean": None,
        "consistency_std": None,
        "trend": None,  # "improving", "declining", "stable"
    }
    
    if current_value is None:
        return result
    
    # Filter out None values
    valid_recent = [v for v in recent_values if v is not None]
    
    if not valid_recent:
        return result
    
    # Delta vs last swing
    result["delta_vs_last"] = round(current_value - valid_recent[0], 3)
    
    # Delta vs mean
    mean_val = np.mean(valid_recent)
    result["delta_vs_mean"] = round(current_value - mean_val, 3)
    
    # Consistency (std dev of recent values)
    if len(valid_recent) >= 2:
        result["consistency_std"] = round(float(np.std(valid_recent)), 3)
    
    # Simple trend analysis
    if len(valid_recent) >= 2:
        # Compare first half to second half
        mid = len(valid_recent) // 2
        first_half_mean = np.mean(valid_recent[:mid]) if mid > 0 else valid_recent[0]
        second_half_mean = np.mean(valid_recent[mid:])
        
        # Trend direction (newer values in first half)
        diff = first_half_mean - second_half_mean
        threshold = result.get("consistency_std", 1.0) * 0.5 if result.get("consistency_std") else 1.0
        
        if abs(diff) < threshold:
            result["trend"] = "stable"
        elif diff > 0:
            result["trend"] = "improving"  # Getting higher (may be good or bad)
        else:
            result["trend"] = "declining"  # Getting lower
    
    return result


def compute_improvement_delta(
    current: Dict[str, Any],
    recent: List[Dict[str, Any]],
    metric_names: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Compute improvement deltas for current swing vs recent swings.
    
    Args:
        current: Current swing's metrics dict
        recent: List of previous swings' metrics (newest first)
        metric_names: Optional list of metrics to analyze. 
                     If None, uses KEY_METRICS.
    
    Returns:
        Dict mapping metric_name to delta statistics:
        {
            "x_factor_top_deg": {
                "current": 45.5,
                "delta_vs_last": 2.3,
                "delta_vs_mean": 1.1,
                "consistency_std": 3.2,
                "trend": "improving"
            },
            ...
        }
    """
    if metric_names is None:
        metric_names = KEY_METRICS
    
    result = {}
    
    for name in metric_names:
        current_value = current.get(name)
        
        # Collect recent values for this metric
        recent_values = []
        for swing in recent:
            if isinstance(swing, dict):
                val = swing.get(name)
                recent_values.append(val)
        
        delta = compute_metric_delta(current_value, recent_values)
        
        if current_value is not None:
            delta["current"] = current_value
            result[name] = delta
    
    return result


def summarize_improvement(deltas: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a high-level summary of improvement across all metrics.
    
    Returns:
        Dict with overall improvement stats and highlights.
    """
    summary = {
        "metrics_improved": 0,
        "metrics_declined": 0,
        "metrics_stable": 0,
        "most_improved": None,
        "needs_attention": None,
        "consistency_score": None,
    }
    
    improvements = []
    declines = []
    stds = []
    
    for name, data in deltas.items():
        if data.get("trend") == "improving":
            summary["metrics_improved"] += 1
            if data.get("delta_vs_mean") is not None:
                improvements.append((name, abs(data["delta_vs_mean"])))
        elif data.get("trend") == "declining":
            summary["metrics_declined"] += 1
            if data.get("delta_vs_mean") is not None:
                declines.append((name, abs(data["delta_vs_mean"])))
        else:
            summary["metrics_stable"] += 1
        
        if data.get("consistency_std") is not None:
            stds.append(data["consistency_std"])
    
    # Most improved metric
    if improvements:
        improvements.sort(key=lambda x: x[1], reverse=True)
        summary["most_improved"] = improvements[0][0]
    
    # Metric needing most attention
    if declines:
        declines.sort(key=lambda x: x[1], reverse=True)
        summary["needs_attention"] = declines[0][0]
    
    # Overall consistency score (lower std = more consistent)
    if stds:
        avg_std = np.mean(stds)
        # Convert to 0-100 score (lower std = higher score)
        # Assume std of 5 is average, score = 100 at std=0
        consistency = max(0, min(100, 100 - (avg_std * 10)))
        summary["consistency_score"] = round(consistency, 1)
    
    return summary


def format_delta_for_display(
    delta: Dict[str, Any],
    metric_name: str,
    higher_is_better: bool = True
) -> Dict[str, Any]:
    """
    Format delta data for UI display.
    
    Args:
        delta: Delta data from compute_metric_delta
        metric_name: Name of the metric
        higher_is_better: Whether higher values are desirable
    
    Returns:
        Dict with formatted strings and status indicators.
    """
    result = {
        "label": metric_name.replace("_", " ").title(),
        "delta_text": None,
        "status": None,  # "better", "worse", "same"
        "consistency_text": None,
    }
    
    delta_vs_last = delta.get("delta_vs_last")
    
    if delta_vs_last is not None:
        sign = "+" if delta_vs_last > 0 else ""
        result["delta_text"] = f"{sign}{delta_vs_last:.1f}"
        
        # Determine if change is good or bad
        if abs(delta_vs_last) < 0.5:
            result["status"] = "same"
        elif (delta_vs_last > 0) == higher_is_better:
            result["status"] = "better"
        else:
            result["status"] = "worse"
    
    std = delta.get("consistency_std")
    if std is not None:
        if std < 2:
            result["consistency_text"] = "Very consistent"
        elif std < 5:
            result["consistency_text"] = "Consistent"
        elif std < 10:
            result["consistency_text"] = "Variable"
        else:
            result["consistency_text"] = "Inconsistent"
    
    return result

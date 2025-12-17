"""
Club-based Metric Normalization - Score metrics based on club-specific targets.

Loads target ranges from config/club_metric_targets.json and provides
normalized scoring (0-1) with LOW/OK/HIGH flags.
"""

import json
import os
from typing import Dict, Any, Optional, Literal
from functools import lru_cache


# Path to config file
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config",
    "club_metric_targets.json"
)


@lru_cache(maxsize=1)
def _load_club_targets() -> Dict[str, Dict[str, list]]:
    """Load club metric targets from JSON config file."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[club_normalization] Warning: Could not load config: {e}")
        return {}


def get_metric_range(
    metric_name: str,
    club_type: str
) -> Optional[tuple]:
    """
    Get the [low, high] acceptable range for a metric and club type.
    
    Args:
        metric_name: Name of the metric (e.g., 'x_factor_top_deg')
        club_type: Club type (e.g., 'driver', 'mid_iron', 'wedge')
    
    Returns:
        Tuple (low, high) or None if not found.
    """
    targets = _load_club_targets()
    
    # Normalize club type
    club_type = club_type.lower().replace(" ", "_")
    
    # Try exact match first
    club_targets = targets.get(club_type)
    
    # Fallback mappings
    if club_targets is None:
        if "iron" in club_type:
            club_targets = targets.get("iron")
        elif "wood" in club_type or "fairway" in club_type:
            club_targets = targets.get("wood")
        elif "driver" in club_type:
            club_targets = targets.get("driver")
        else:
            # Default to mid_iron as generic fallback
            club_targets = targets.get("mid_iron", targets.get("iron"))
    
    if club_targets is None:
        return None
    
    range_val = club_targets.get(metric_name)
    if range_val is None or len(range_val) != 2:
        return None
    
    return (range_val[0], range_val[1])


def normalize_metric(
    value: float,
    metric_name: str,
    club_type: str
) -> Dict[str, Any]:
    """
    Normalize a metric value based on club-specific targets.
    
    Scoring:
    - 0.0 = far outside range
    - 0.5 = at range boundary
    - 1.0 = at center of range
    
    Args:
        value: The metric value to normalize
        metric_name: Name of the metric
        club_type: Club type for lookup
    
    Returns:
        Dict with:
        - score: 0.0 to 1.0 normalized score
        - flag: "LOW" | "OK" | "HIGH"
        - range: [low, high] if found
    """
    result: Dict[str, Any] = {
        "score": None,
        "flag": None,
        "range": None,
    }
    
    if value is None:
        return result
    
    range_val = get_metric_range(metric_name, club_type)
    if range_val is None:
        # No range defined, can't normalize
        return result
    
    low, high = range_val
    result["range"] = [low, high]
    
    # Calculate where value falls relative to range
    center = (low + high) / 2
    half_width = (high - low) / 2
    
    if half_width < 0.001:
        # Degenerate range
        if abs(value - center) < 0.001:
            result["score"] = 1.0
            result["flag"] = "OK"
        else:
            result["score"] = 0.0
            result["flag"] = "HIGH" if value > center else "LOW"
        return result
    
    # Distance from center, normalized
    dist_from_center = abs(value - center)
    normalized_dist = dist_from_center / half_width
    
    # Determine flag
    if value < low:
        result["flag"] = "LOW"
    elif value > high:
        result["flag"] = "HIGH"
    else:
        result["flag"] = "OK"
    
    # Score calculation:
    # - Within range: score = 1.0 - (dist_from_center / half_width) * 0.5
    #   So center = 1.0, edges = 0.5
    # - Outside range: score = 0.5 - (excess / half_width) * 0.25
    #   So decreases as you get further from range
    
    if low <= value <= high:
        # Within range: 0.5 to 1.0
        score = 1.0 - (normalized_dist * 0.5)
    else:
        # Outside range: 0.0 to 0.5
        excess = dist_from_center - half_width
        excess_normalized = excess / half_width
        score = max(0.0, 0.5 - (excess_normalized * 0.25))
    
    result["score"] = round(score, 3)
    
    return result


def normalize_metrics_batch(
    metrics: Dict[str, float],
    club_type: str,
    metric_names: Optional[list] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Normalize multiple metrics at once.
    
    Args:
        metrics: Dict of metric_name -> value
        club_type: Club type for all metrics
        metric_names: Optional list of metrics to normalize.
                     If None, normalizes all known metrics.
    
    Returns:
        Dict of metric_name -> normalization result
    """
    result = {}
    
    if metric_names is None:
        # Get list of known metrics from config
        targets = _load_club_targets()
        club_targets = targets.get(club_type.lower(), targets.get("iron", {}))
        metric_names = [k for k in club_targets.keys() if not k.startswith("_")]
    
    for name in metric_names:
        value = metrics.get(name)
        if value is not None:
            result[name] = normalize_metric(value, name, club_type)
    
    return result


def get_available_clubs() -> list:
    """Get list of available club types in config."""
    targets = _load_club_targets()
    return list(targets.keys())


def get_metrics_for_club(club_type: str) -> list:
    """Get list of metrics defined for a club type."""
    targets = _load_club_targets()
    club_targets = targets.get(club_type.lower(), {})
    return [k for k in club_targets.keys() if not k.startswith("_")]

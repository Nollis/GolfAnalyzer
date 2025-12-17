
from typing import Any

def _format_metric_value(metric_key: str, value: Any) -> str:
    """Format metric value with appropriate units."""
    if value is None:
        return "N/A"
    
    if isinstance(value, (int, float)):
        if "ratio" in metric_key or "tempo" in metric_key:
            return f"{value:.2f}:1"
        elif "deg" in metric_key or "angle" in metric_key:
            return f"{value:.1f}°"
        elif "ms" in metric_key or "duration" in metric_key:
            return f"{value/1000:.2f}s"
        elif "range" in metric_key or "amount" in metric_key:
            return f"{value:.3f}"
        else:
            return f"{value:.1f}"
    
    return str(value)

# Test cases
keys = [
    "tempo_ratio", 
    "backswing_duration_ms", 
    "downswing_duration_ms", 
    "trail_elbow_impact_deg"
]
values = [3.0, 1100.0, 367.0, 117.2]

print("--- Formatting Test ---")
for k, v in zip(keys, values):
    formatted = _format_metric_value(k, v)
    print(f"Key: {k}, Value: {v} -> Formatted: '{formatted}'")

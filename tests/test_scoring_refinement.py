import sys
import os
import pytest
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schemas import SwingMetrics
from reference.reference_profiles import get_reference_profile_for
from reference.scoring import Scorer

def test_good_dtl_swing():
    print("\n--- Testing Good DTL Swing ---")
    # User's example of a "good junior swing"
    metrics = SwingMetrics(
        tempo_ratio=3.0,
        chest_turn_top_deg=38.8,
        pelvis_turn_top_deg=20.8,
        x_factor_top_deg=18.0,
        spine_angle_address_deg=18.0,
        spine_angle_impact_deg=16.6,
        lead_arm_address_deg=170.0,
        lead_arm_top_deg=171.0,
        lead_arm_impact_deg=127.7,
        trail_elbow_top_deg=78.4,
        knee_flex_left_address_deg=165.0,
        knee_flex_right_address_deg=165.0,
        head_sway_range=0.058,
        early_extension_amount=0.03,
        # Missing values should be ignored
        backswing_duration_ms=None,
        downswing_duration_ms=None
    )
    
    ref = get_reference_profile_for(club_type="iron", view="dtl")
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref)
    
    print(f"Overall Score: {scores.overall_score}")
    for key, ms in scores.metric_scores.items():
        print(f"{key}: {ms.value:.2f} -> {ms.score} (Target: {ms.target_min:.1f}-{ms.target_max:.1f})")
        
    # Assertions
    assert 85 <= scores.overall_score <= 95, f"Score {scores.overall_score} should be between 85 and 95"
    
    # Check specific metrics are not red
    assert scores.metric_scores["tempo_ratio"].score == "green"
    assert scores.metric_scores["chest_turn_top_deg"].score != "red" # Should be green/yellow
    assert scores.metric_scores["lead_arm_impact_deg"].score != "red" # Should be green/yellow (127.7 is in 125-175 range)

def test_bad_dtl_swing():
    print("\n--- Testing Bad DTL Swing ---")
    metrics = SwingMetrics(
        tempo_ratio=1.5, # Very fast/bad
        chest_turn_top_deg=10.0, # No turn
        pelvis_turn_top_deg=5.0,
        x_factor_top_deg=5.0,
        spine_angle_address_deg=0.0, # Too upright
        head_sway_range=0.20, # Huge sway
        early_extension_amount=0.15, # Huge EE
        # Others ok-ish
        lead_arm_top_deg=170.0,
        knee_flex_left_address_deg=165.0,
    )
    
    ref = get_reference_profile_for(club_type="driver", view="dtl")
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref)
    
    print(f"Overall Score: {scores.overall_score}")
    for key, ms in scores.metric_scores.items():
        print(f"{key}: {ms.value:.2f} -> {ms.score}")
        
    # Assertions
    assert scores.overall_score < 50, f"Score {scores.overall_score} should be < 50"
    assert scores.metric_scores["tempo_ratio"].score == "red"
    assert scores.metric_scores["head_sway_range"].score == "red"
    assert scores.metric_scores["early_extension_amount"].score == "red"

def test_dtl_zero_weight_metric_not_affect_total():
    print("\n--- Testing DTL Zero Weight Metric ---")
    """
    If a metric like chest_turn_top_deg has weight=0 in DTL,
    it should not drag down the overall score even when it's red.
    """
    # Construct a swing with good core metrics but terrible chest turn
    metrics = SwingMetrics(
        tempo_ratio=3.0,
        chest_turn_top_deg=5.0,      # absurdly low -> should be red
        pelvis_turn_top_deg=5.0,     # also bad
        x_factor_top_deg=0.0,
        spine_angle_address_deg=18.0,
        spine_angle_impact_deg=16.0,
        lead_arm_impact_deg=150.0,
        trail_elbow_top_deg=80.0,
        knee_flex_left_address_deg=165.0,
        knee_flex_right_address_deg=165.0,
        head_sway_range=0.05,
        early_extension_amount=0.03,
    )

    ref = get_reference_profile_for(club_type="iron", view="dtl")
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref)
    
    print(f"Overall Score: {scores.overall_score}")
    print(f"Chest Turn Score: {scores.metric_scores['chest_turn_top_deg'].score}")

    # Chest/pelvis/X-factor may be red…
    assert scores.metric_scores["chest_turn_top_deg"].score == "red"

    # …but overall score should still be high because those metrics have weight=0 in DTL
    assert scores.overall_score >= 70, (
        f"Overall score should not be dragged down by zero-weight metrics, got {scores.overall_score}"
    )

if __name__ == "__main__":
    try:
        test_good_dtl_swing()
        test_bad_dtl_swing()
        test_dtl_zero_weight_metric_not_affect_total()
        print("\nALL TESTS PASSED")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

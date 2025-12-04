from app.services.skill_assessment import SkillAssessmentService
from app.schemas import SwingMetrics, SwingScores, MetricScore

def test_skill_assessment():
    service = SkillAssessmentService()
    
    # Mock Metrics (doesn't matter much for current simple logic, but good for future)
    metrics = SwingMetrics(
        tempo_ratio=3.0, backswing_duration_ms=800, downswing_duration_ms=266,
        shoulder_turn_top_deg=90, hip_turn_top_deg=45, spine_tilt_address_deg=0,
        spine_tilt_impact_deg=0, head_movement_forward_cm=0, head_movement_vertical_cm=0,
        shaft_lean_impact_deg=0,
        lead_wrist_flexion_address_deg=0, lead_wrist_flexion_top_deg=0,
        lead_wrist_flexion_impact_deg=0, lead_wrist_hinge_top_deg=0
    )
    
    # Test Pro
    scores_pro = SwingScores(overall_score=95, metric_scores=[])
    skill = service.assess_skill_level(metrics, scores_pro)
    print(f"Score 95 -> Skill: {skill} (Expected: Pro)")
    assert skill == "Pro"
    
    # Test Advanced
    scores_adv = SwingScores(overall_score=85, metric_scores=[])
    skill = service.assess_skill_level(metrics, scores_adv)
    print(f"Score 85 -> Skill: {skill} (Expected: Advanced)")
    assert skill == "Advanced"
    
    # Test Intermediate
    scores_int = SwingScores(overall_score=70, metric_scores=[])
    skill = service.assess_skill_level(metrics, scores_int)
    print(f"Score 70 -> Skill: {skill} (Expected: Intermediate)")
    assert skill == "Intermediate"
    
    # Test Beginner
    scores_beg = SwingScores(overall_score=50, metric_scores=[])
    skill = service.assess_skill_level(metrics, scores_beg)
    print(f"Score 50 -> Skill: {skill} (Expected: Beginner)")
    assert skill == "Beginner"

if __name__ == "__main__":
    test_skill_assessment()

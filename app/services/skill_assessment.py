from app.schemas import SwingMetrics, SwingScores

class SkillAssessmentService:
    def assess_skill_level(self, metrics: SwingMetrics, scores: SwingScores, current_handicap: float = 0.0) -> str:
        """
        Assess skill level based on swing consistency and quality.
        Returns: "Beginner", "Intermediate", "Advanced", "Pro"
        """
        
        # 1. Use Handicap if available and reliable (e.g. < 30)
        # If handicap is 0.0, it might be default/unset, so ignore unless we know it's real.
        # Let's assume if it's explicitly set to something non-zero or we trust it.
        # But for now, let's rely on the swing score.
        
        overall_score = scores.overall_score
        
        # Basic heuristic based on overall score (0-100)
        # Pro: 90+
        # Advanced: 80-89
        # Intermediate: 60-79
        # Beginner: < 60
        
        # Also check specific "killer" metrics
        # e.g. Tempo. Pros are almost always 3.0 +/- 0.2
        tempo_good = 2.8 <= metrics.tempo_ratio <= 3.2
        
        # Shoulder turn. Pros > 85
        turn_good = metrics.shoulder_turn_top_deg > 85
        
        if overall_score >= 90:
            return "Pro"
        elif overall_score >= 80:
            return "Advanced"
        elif overall_score >= 60:
            return "Intermediate"
        else:
            return "Beginner"

    def update_user_skill(self, user, metrics: SwingMetrics, scores: SwingScores):
        """
        Update user's skill level if the new assessment is higher?
        Or just average?
        For now, let's just update it to the latest assessment to keep it dynamic.
        """
        new_skill = self.assess_skill_level(metrics, scores, user.handicap)
        
        # Logic to prevent downgrading too easily?
        # Maybe only upgrade?
        # Or maybe "Intermediate" -> "Beginner" is valid if they are struggling.
        # Let's just set it.
        
        user.skill_level = new_skill
        return new_skill

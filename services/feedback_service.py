import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.schemas import SwingMetrics, SwingScores, SwingFeedback, Drill, MetricScore
from reference.reference_profiles import get_reference_profile_for, ReferenceProfile

class FeedbackService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print(f"DEBUG: FeedbackService using API key starting with: {api_key[:8]}...")
        else:
            print("DEBUG: FeedbackService found NO API key")
        # If no key is provided, we might want to mock or fail gracefully.
        # For now, we'll assume it's there or the client will raise an error.
        self.client = OpenAI(api_key=api_key) if api_key else None

    def generate_feedback(
        self, 
        metrics: SwingMetrics, 
        scores: SwingScores, 
        handedness: str, 
        club_type: str,
        reference_profile: Optional[ReferenceProfile] = None
    ) -> SwingFeedback:
        """
        Generate AI-powered coaching feedback based on swing metrics.
        
        Args:
            metrics: Computed swing metrics
            scores: Metric scores (green/yellow/red ratings)
            handedness: "Right" or "Left"
            club_type: Type of club used
            reference_profile: Optional reference profile for target values
        """
        if not self.client:
            return self._mock_feedback("OpenAI API Key not found. Returning mock feedback.")

        # Get reference profile for target values if not provided
        if reference_profile is None:
            reference_profile = get_reference_profile_for(club_type, "face_on")  # Default view
        
        # Construct the prompt with better context
        system_prompt = """
You are an expert golf coach with deep knowledge of biomechanics and swing mechanics. 
You will be provided with biomechanical metrics from a student's golf swing, along with:
- Current values for each metric
- Performance ratings (green = good, yellow = needs improvement, red = poor)
- Target/ideal values for comparison

Your task is to analyze these metrics and provide actionable coaching feedback.

IMPORTANT GUIDELINES:
1. Focus on the metrics marked as "red" or "yellow" first - these need the most attention
2. Explain WHY each issue matters (e.g., "Early extension causes loss of power because...")
3. Provide specific, actionable drills that address the root causes
4. Prioritize issues that have the biggest impact on swing quality
5. Be encouraging but honest - acknowledge what's working well
6. Consider the relationship between metrics (e.g., tempo affects everything)
7. DO NOT guess about video content - ONLY use the provided metrics

Output must be a valid JSON object with the following structure:
{
    "summary": "2-3 sentences summarizing overall swing performance, highlighting strengths and main areas for improvement.",
    "priority_issues": [
        "Issue 1: Specific problem with explanation of why it matters",
        "Issue 2: Another specific problem",
        "Issue 3: Third priority issue (max 3)"
    ],
    "drills": [
        {
            "title": "Specific Drill Name",
            "description": "Clear, step-by-step description of how to perform the drill and what it addresses"
        }
    ]
}

Keep drills practical and specific. Each drill should directly address one of the priority issues.
"""

        # Prepare user message with better formatted data
        metrics_summary = self._format_metrics_for_prompt(metrics, scores, reference_profile)
        user_message = f"""
Student Profile:
- Handedness: {handedness}
- Club Type: {club_type}
- Overall Score: {scores.overall_score}/100

Swing Metrics Analysis:
{metrics_summary}

Provide coaching feedback in JSON format. Focus on actionable improvements based on the metrics above.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # More cost-effective than gpt-4o
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000  # Limit response length
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            drills = [Drill(**d) for d in data.get("drills", [])]
            
            return SwingFeedback(
                summary=data.get("summary", "No summary provided."),
                priority_issues=data.get("priority_issues", []),
                drills=drills
            )

        except Exception as e:
            print(f"Error generating feedback: {e}")
            return self._mock_feedback(f"Error generating feedback: {str(e)}")

    def _format_metrics_for_prompt(
        self, 
        metrics: SwingMetrics, 
        scores: SwingScores,
        reference_profile: ReferenceProfile
    ) -> str:
        """
        Format metrics in a readable way for the AI prompt, including target values.
        """
        # Metric display names mapping
        metric_names = {
            "tempo_ratio": "Tempo Ratio",
            "backswing_duration_ms": "Backswing Duration",
            "downswing_duration_ms": "Downswing Duration",
            "chest_turn_top_deg": "Chest Turn (at top)",
            "pelvis_turn_top_deg": "Pelvis Turn (at top)",
            "x_factor_top_deg": "X-Factor (at top)",
            "spine_angle_address_deg": "Spine Angle (address)",
            "spine_angle_impact_deg": "Spine Angle (impact)",
            "lead_arm_address_deg": "Lead Arm (address)",
            "lead_arm_top_deg": "Lead Arm (at top)",
            "lead_arm_impact_deg": "Lead Arm (impact)",
            "trail_elbow_address_deg": "Trail Elbow (address)",
            "trail_elbow_top_deg": "Trail Elbow (at top)",
            "trail_elbow_impact_deg": "Trail Elbow (impact)",
            "knee_flex_left_address_deg": "Lead Knee Flex (address)",
            "knee_flex_right_address_deg": "Trail Knee Flex (address)",
            "head_sway_range": "Head Stability (lateral movement)",
            "early_extension_amount": "Early Extension",
        }
        
        # Get metrics dict (handle both Pydantic v1 and v2)
        try:
            m_dict = metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics.dict()
        except Exception:
            m_dict = metrics.dict()
        
        s_dict = scores.metric_scores
        
        lines = []
        
        # Group metrics by category for better organization
        categories = {
            "Timing & Tempo": ["tempo_ratio", "backswing_duration_ms", "downswing_duration_ms"],
            "Rotation": ["chest_turn_top_deg", "pelvis_turn_top_deg", "x_factor_top_deg"],
            "Posture": ["spine_angle_address_deg", "spine_angle_impact_deg"],
            "Arm Positions": [
                "lead_arm_address_deg", "lead_arm_top_deg", "lead_arm_impact_deg",
                "trail_elbow_address_deg", "trail_elbow_top_deg", "trail_elbow_impact_deg"
            ],
            "Lower Body": [
                "knee_flex_left_address_deg", "knee_flex_right_address_deg"
            ],
            "Head Movement": ["head_sway_range", "early_extension_amount"]
        }
        
        for category, metric_keys in categories.items():
            category_lines = []
            for key in metric_keys:
                if key not in m_dict:
                    continue
                    
                val = m_dict[key]
                if val is None:
                    continue
                    
                score_info = s_dict.get(key)
                rating = score_info.score if score_info else "unknown"
                
                # Get target values from reference profile
                target_info = reference_profile.targets.get(key)
                if target_info:
                    target_str = f"Target: {target_info.ideal_val:.1f} (range: {target_info.min_val:.1f}-{target_info.max_val:.1f})"
                else:
                    target_str = "No target available"
                
                # Format value based on metric type
                display_name = metric_names.get(key, key.replace("_", " ").title())
                formatted_val = self._format_metric_value(key, val)
                
                # Color code rating
                rating_emoji = {
                    "green": "✅",
                    "yellow": "⚠️",
                    "red": "❌"
                }.get(rating, "❓")
                
                category_lines.append(
                    f"  {rating_emoji} {display_name}: {formatted_val} | Rating: {rating.upper()} | {target_str}"
                )
            
            if category_lines:
                lines.append(f"\n{category}:")
                lines.extend(category_lines)
        
        return "\n".join(lines)
    
    def _format_metric_value(self, metric_key: str, value: Any) -> str:
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

    def _mock_feedback(self, reason: str) -> SwingFeedback:
        """Return mock feedback when AI generation is unavailable."""
        
        # Check if it's an auth/key error
        is_auth_error = any(x in str(reason).lower() for x in ["401", "api key", "unauthorized", "invalid_api_key"])
        
        if is_auth_error:
            summary = f"Feedback generation unavailable: {reason}. Please configure OpenAI API key for AI-powered coaching feedback."
            priority_issues = ["Configure OpenAI API key in environment variables"]
        else:
            summary = f"Feedback generation unavailable. Error: {reason}"
            priority_issues = ["Feedback generation failed. Please try regenerating."]

        return SwingFeedback(
            summary=summary,
            priority_issues=priority_issues,
            drills=[
                Drill(
                    title="Review Your Metrics",
                    description="Focus on metrics marked in red or yellow. Compare your values to the target ranges shown."
                )
            ]
        )

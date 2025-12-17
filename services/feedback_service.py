import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.schemas import SwingMetrics, SwingScores, SwingFeedback, MetricScore, DrillResponse
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
        db: Optional[Any] = None, # Use Any to avoid circular imports at top level if needed, or import appropriately
        reference_profile: Optional[ReferenceProfile] = None
    ) -> SwingFeedback:
        """
        Generate AI-powered coaching feedback based on swing metrics.
        """
        # --- 1. Identify Priority Issues from Scores ---
        priority_metrics = []
        for metric_key, score_info in scores.metric_scores.items():
            if score_info.score in ["red", "yellow"]:
                weight = getattr(score_info, 'weight', 1.0)
                if weight > 0:
                    priority_metrics.append((metric_key, score_info.score, weight))
        
        # Sort by severity (red first) then weight
        priority_metrics.sort(key=lambda x: (0 if x[1] == 'red' else 1, -x[2]))
        top_issues = priority_metrics[:3]
        
        # --- 2. Query DB for Drills (Deterministic) ---
        final_drills = []
        if db:
            from app.models.drill import Drill as DrillModel
            
            # Collect target metrics we need drills for
            target_metrics = [issue[0] for issue in top_issues]
            
            if target_metrics:
                # Find drills that target these metrics
                found_drills = db.query(DrillModel).filter(DrillModel.target_metric.in_(target_metrics)).all()
                
                # Convert to Schema format and prioritize
                # We want to match them to the highest priority issues first
                for issue_key, _, _ in top_issues:
                    # Find drills for this specific issue
                    matching = [d for d in found_drills if d.target_metric == issue_key]
                    for d in matching:
                        # Avoid duplicates
                        if not any(fd.id == d.id for fd in final_drills):
                            final_drills.append(DrillResponse(
                                id=d.id,
                                title=d.title,
                                description=d.description,
                                category=d.category,
                                difficulty=d.difficulty,
                                video_url=d.video_url,
                                target_metric=d.target_metric
                            ))
                            
                    if len(final_drills) >= 3:
                        break
                
                # Trim to top 3
                final_drills = final_drills[:3]
        
        # --- 3. Generate AI Feedback (Analysis Only) ---
        if not self.client:
             # If no AI, return DB drills only (or mock)
            return self._mock_feedback("OpenAI API Key not found.", final_drills)

        # Get reference profile for target values if not provided
        if reference_profile is None:
            reference_profile = get_reference_profile_for(club_type, "face_on")  # Default view
        
        # Construct the prompt (Analysis Focused)
        system_prompt = """
You are an expert golf coach with deep knowledge of biomechanics and swing mechanics. 
You will be provided with biomechanical metrics from a student's golf swing, along with:
- Current values for each metric
- Performance ratings (green = good, yellow = needs improvement, red = poor)
- Target/ideal values for comparison

Your task is to analyze these metrics and provide actionable coaching feedback.

GUIDELINES:
1. Focus on the metrics marked as "red" or "yellow" first. These are the Priority Issues.
2. Explain WHY each issue matters.
3. BE SPECIFIC.
4. Do NOT Suggest Drills. The integration system handles drill recommendations separately. Focus only on the analysis of the fault.
5. Output valid JSON.

Structure:
{
    "summary": "2-3 sentences summarizing overall performance.",
    "priority_issues": ["Issue 1: ...", "Issue 2: ..."],
    "phase_feedback": { "address": "...", "top": "...", "impact": "...", "finish": "..." }
}
"""
        # Prepare user message
        metrics_summary = self._format_metrics_for_prompt(metrics, scores, reference_profile)
        
        user_message = f"""
Student Profile:
- Handedness: {handedness}
- Club Type: {club_type}
- Overall Score: {scores.overall_score}/100

Swing Metrics Analysis:
{metrics_summary}

Provide coaching feedback in JSON format.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            return SwingFeedback(
                summary=data.get("summary", "No summary provided."),
                priority_issues=data.get("priority_issues", []),
                drills=final_drills, # Use deterministic list
                phase_feedback=data.get("phase_feedback", {})
            )

        except Exception as e:
            print(f"Error generating feedback: {e}")
            return self._mock_feedback(f"Error generating feedback: {str(e)}", final_drills)

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
        
        shown_keys = set()
        
        
        # Define deprecated metrics to skip
        deprecated_metrics = {
            "shoulder_turn_top_deg", 
            "hip_turn_top_deg", 
            "spine_tilt_address_deg", 
            "spine_tilt_impact_deg",
            "head_movement_forward_cm",
            "head_movement_vertical_cm",
            "shaft_lean_impact_deg",
            "lead_wrist_flexion_address_deg",
            "lead_wrist_flexion_top_deg",
            "lead_wrist_flexion_impact_deg",
            "lead_wrist_hinge_top_deg"
        }

        for category, metric_keys in categories.items():
            category_lines = []
            for key in metric_keys:
                if key not in m_dict:
                    continue

                if key in deprecated_metrics:
                    print(f"DEBUG: Skipping deprecated metric: {key}")
                    continue
                    
                val = m_dict[key]
                if val is None:
                    continue
                    
                score_info = s_dict.get(key)
                if not score_info:
                    # Metric exists but no score info (e.g. unweighted or new metric without target)
                    # Include it as context
                    rating = None
                    target_str = "(Context Only)"
                else:
                    rating = score_info.score
                    # Check if unweighted
                    if getattr(score_info, 'weight', 1.0) <= 0.0:
                        rating = None # Treat as context only
                        target_str = "(Unweighted)"
                    else:
                        # Get target values from reference profile
                        target_info = reference_profile.targets.get(key)
                        if target_info:
                            tgt_str = self._format_metric_value(key, target_info.ideal_val)
                            min_str = self._format_metric_value(key, target_info.min_val)
                            max_str = self._format_metric_value(key, target_info.max_val)
                            target_str = f"Target: {tgt_str} (range: {min_str}-{max_str})"
                        else:
                            target_str = "No target available"
                
                # Format value
                display_name = metric_names.get(key, key.replace("_", " ").title())
                formatted_val = self._format_metric_value(key, val)
                
                if rating:
                    rating_emoji = {
                        "green": "✅",
                        "yellow": "⚠️",
                        "red": "❌"
                    }.get(rating, "❓")
                    line = f"  {rating_emoji} {display_name}: {formatted_val} | Rating: {rating.upper()} | {target_str}"
                else:
                    # Display as informational context
                    line = f"  ℹ️ {display_name}: {formatted_val} | {target_str}"
                
                category_lines.append(line)
                shown_keys.add(key)
            
            if category_lines:
                lines.append(f"\n{category}:")
                lines.extend(category_lines)
                
        # Add any remaining metrics that weren't included in categories or didn't have scores
        # This ensures the AI sees *all* data even if we don't have a target/rating for it
        additional_lines = []
        for key, val in m_dict.items():
            if key in shown_keys:
                continue
            if val is None:
                continue
            # Skip internal or irrelevant fields if any
            if key in ["session_id", "user_id", "video_url"]:
                continue
            
            # Debug key
            # print(f"Processing key: '{key}'") 

            # Check deprecated metrics
            if key in deprecated_metrics:
                # print(f"Skipping deprecated: {key}")
                continue
                
            display_name = metric_names.get(key, key.replace("_", " ").title())
            formatted_val = self._format_metric_value(key, val)
            
            # Check if we have a score but it was skipped due to weight/category logic
            rating_str = ""
            score_info = s_dict.get(key)
            if score_info and score_info.score:
                 # Check if we skipped it earlier (e.g. weight 0)
                 if getattr(score_info, 'weight', 1.0) <= 0.0:
                     rating_str = " | (Unweighted)"
                 else:
                     rating_str = f" | Rating: {score_info.score.upper()}"
            
            additional_lines.append(f"  ℹ️ {display_name}: {formatted_val}{rating_str}")

        if additional_lines:
            lines.append("\nAdditional Context:")
            lines.extend(additional_lines)

        return "\n".join(lines)
    
    def _format_metric_value(self, metric_key: str, value: Any) -> str:
        """Format metric value with appropriate units."""
        if value is None:
            return "N/A"
        
        if isinstance(value, (int, float)):
            # Explicit key checks first
            if "duration" in metric_key or "ms" in metric_key:
                 return f"{value/1000:.2f}s"
            
            if "ratio" in metric_key or "tempo" in metric_key:
                return f"{value:.2f}:1"
            
            if "deg" in metric_key or "angle" in metric_key:
                return f"{value:.1f}°"
            
            if "range" in metric_key or "amount" in metric_key or "index" in metric_key:
                return f"{value:.3f}"
            
            return f"{value:.1f}"
        
        return str(value)

    def _mock_feedback(self, reason: str, drills: List[DrillResponse] = []) -> SwingFeedback:
        """Return mock feedback when AI generation is unavailable."""
        
        # Check if it's an auth/key error
        is_auth_error = any(x in str(reason).lower() for x in ["401", "api key", "unauthorized", "invalid_api_key"])
        
        if is_auth_error:
            summary = f"Feedback generation unavailable: {reason}. Please configure OpenAI API key for AI-powered coaching feedback."
            priority_issues = ["Configure OpenAI API key in environment variables"]
        else:
            summary = f"Feedback generation unavailable. Error: {reason}"
            priority_issues = ["Feedback generation failed. Please try regenerating."]

        if not drills:
            # Fallback mock drill if no DB drills provided
            drills = [
                 DrillResponse(
                    id="mock-id",
                    title="Review Your Metrics",
                    description="Focus on metrics marked in red or yellow.",
                    category="General",
                    difficulty="All Levels"
                )
            ]

        return SwingFeedback(
            summary=summary,
            priority_issues=priority_issues,
            drills=drills,
            phase_feedback={}
        )

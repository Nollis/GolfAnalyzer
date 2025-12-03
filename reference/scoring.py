from typing import Dict
from app.schemas import SwingMetrics, SwingScores, MetricScore
from reference.reference_profiles import ReferenceProfile, MetricTarget

class Scorer:
    def build_scores(self, metrics: SwingMetrics, ref: ReferenceProfile) -> SwingScores:
        metric_scores: Dict[str, MetricScore] = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        metrics_dict = metrics.dict()

        for key, target in ref.targets.items():
            val = metrics_dict.get(key)
            if val is None:
                continue

            # Determine Red/Yellow/Green
            # Simple logic: 
            # Green: within [min, max]
            # Yellow: within [min - tolerance, max + tolerance] (say 20% wider)
            # Red: outside
            
            range_span = target.max_val - target.min_val
            if range_span == 0: range_span = 1.0 # Avoid div/0
            
            # Calculate a 0-100 score for this metric
            # 100 if exactly ideal. 
            # Linear drop off?
            # Let's use a simple tiered approach for the "score" string
            
            score_str = "red"
            numeric_score = 0.0
            
            if target.min_val <= val <= target.max_val:
                score_str = "green"
                numeric_score = 100.0
            else:
                # Check yellow range (e.g. +/- 20% of the range width)
                tolerance = range_span * 0.5 # Generous tolerance
                if (target.min_val - tolerance) <= val <= (target.max_val + tolerance):
                    score_str = "yellow"
                    numeric_score = 50.0
                else:
                    score_str = "red"
                    numeric_score = 0.0
            
            # Refine numeric score based on distance to ideal?
            # For now, keep it simple.
            
            metric_scores[key] = MetricScore(
                value=val,
                score=score_str,
                target_min=target.min_val,
                target_max=target.max_val
            )
            
            total_weighted_score += numeric_score * target.weight
            total_weight += target.weight

        overall_score = 0
        if total_weight > 0:
            overall_score = int(total_weighted_score / total_weight)

        return SwingScores(
            overall_score=overall_score,
            metric_scores=metric_scores
        )

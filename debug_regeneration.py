
from services.feedback_service import FeedbackService
from app.schemas import SwingMetrics, SwingScores, MetricScore
from reference.reference_profiles import get_reference_profile_for
from reference.scoring import Scorer

# Mock an "old" session metric set (missing swing_path_index)
metrics = SwingMetrics(
    tempo_ratio=3.0,
    backswing_duration_ms=1000,
    downswing_duration_ms=330,
    early_extension_amount=0.05
    # swing_path_index is None by default
)

# Build scores
ref = get_reference_profile_for("driver", "dtl")
scorer = Scorer()
scores = scorer.build_scores(metrics, ref)

print(f"Metrics: {metrics.swing_path_index}")
print(f"Scores for swing_path_index: {scores.metric_scores.get('swing_path_index')}")

# Try to generate feedback
service = FeedbackService()
# Mock the client to avoid real API call, just want to test prompt construction logic
class MockClient:
    class chat:
        class completions:
            def create(*args, **kwargs):
                return type('obj', (object,), {"choices": [type('obj', (object,), {"message": type('obj', (object,), {"content": "{}"})})]})

service.client = MockClient()

try:
    feedback = service.generate_feedback(metrics, scores, "Right", "driver", ref)
    print("Feedback generation successful")
except Exception as e:
    print(f"Feedback generation FAILED: {e}")
    import traceback
    traceback.print_exc()

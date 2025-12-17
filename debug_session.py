
import sqlite3
import sys
import os

# Add root to path so we can import reference modules
sys.path.append(os.getcwd())

from reference.reference_profiles import get_reference_profile_for
from reference.scoring import Scorer, calculate_smooth_score
from app.schemas import SwingMetrics

STATS_DB = "golf_analyzer.db"

def analyze_session(session_id):
    conn = sqlite3.connect(STATS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get Session
    cursor.execute("SELECT * FROM swing_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        print(f"Session {session_id} not found.")
        return

    print(f"Session ID: {session['id']}")
    print(f"View: {session['view']}")
    print(f"Club: {session['club_type']}")
    print(f"Overall Score (DB): {session['overall_score']}")
    
    # Get Metrics
    cursor.execute("SELECT * FROM swing_metrics WHERE session_id = ?", (session_id,))
    metrics_row = cursor.fetchone()
    if not metrics_row:
        print("No metrics found.")
        return

    # Convert row to dict
    metrics_dict = dict(metrics_row)
    
    # Construct SwingMetrics object (ignoring ID fields)
    metric_obj = SwingMetrics(**{k: v for k,v in metrics_dict.items() if k in SwingMetrics.__fields__})
    
    # Get Profile
    profile = get_reference_profile_for(session['club_type'], session['view'])
    print(f"\nUsing Profile: {profile.name}")

    # Calculate Scores
    scorer = Scorer()
    scores = scorer.build_scores(metric_obj, profile)
    
    print(f"\nCalculated Overall Score: {scores.overall_score}")
    print("\nMetric Scores:")
    for key, ms in scores.metric_scores.items():
        weight = Scorer().build_scores(metric_obj, profile) # Re-run just to get weights, or cleaner: check ref profile directly, or better, inspect scrore obj?
        # Actually build_scores logic handles weights internally and returns scores. 
        # But we want to print the weight too. 
        # Let's just use the DTL_WEIGHTS/FACE_ON logic here manually to display it, or modify Scorer to return weights.
        # For debug, reading from module map is fine.
        from reference.scoring import DTL_WEIGHTS, FACE_ON_WEIGHTS
        weight_map = FACE_ON_WEIGHTS if session['view'] == "face_on" else DTL_WEIGHTS
        weight = weight_map.get(key, profile.targets[key].weight)
        
        raw_score = calculate_smooth_score(ms.value, profile.targets[key].target, profile.targets[key].inner_tol, profile.targets[key].outer_tol) if key in profile.targets else 'N/A'
        print(f"{key}: {ms.value} -> {ms.score} (Raw: {raw_score}) [Weight: {weight}]")

if __name__ == "__main__":
    analyze_session("8f0f2474-682a-4f5e-8861-2ef2d873633d")

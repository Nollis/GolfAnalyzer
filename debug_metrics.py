import sqlite3
import json

def inspect_metrics():
    db_path = "golf_analyzer.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the most recent session
    cursor.execute("SELECT session_id, metrics FROM swing_sessions ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        print("No sessions found.")
        return

    session_id, metrics_json = row
    print(f"Session ID: {session_id}")
    
    if metrics_json:
        metrics = json.loads(metrics_json)
        print("Metrics found:")
        for k, v in metrics.items():
            print(f"{k}: {v}")
    else:
        print("Metrics column is empty/null.")
        
    conn.close()

if __name__ == "__main__":
    inspect_metrics()

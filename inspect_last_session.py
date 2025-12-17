import sqlite3
import json
import sys

def inspect():
    try:
        conn = sqlite3.connect("golf_analyzer.db", timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Get latest session
        cursor.execute("SELECT id, created_at FROM swing_sessions ORDER BY created_at DESC LIMIT 1")
        session = cursor.fetchone()
        
        if not session:
            print("NO_SESSIONS_FOUND")
            return

        session_id = session['id']
        print(f"SESSION_ID: {session_id}")
        print(f"CREATED: {session['created_at']}")
        
        # 2. Get Phases
        cursor.execute("SELECT * FROM swing_phases WHERE session_id = ?", (session_id,))
        phases = cursor.fetchone()
        if phases:
            print("\nPHASES:")
            for key in phases.keys():
                if key not in ['id', 'session_id']:
                    print(f"  {key}: {phases[key]}")
        else:
            print("\nPHASES: None")

        # 3. Get Metrics
        cursor.execute("SELECT * FROM swing_metrics WHERE session_id = ?", (session_id,))
        metrics = cursor.fetchone()
        if metrics:
            print("\nMETRICS:")
            for key in metrics.keys():
                if key not in ['id', 'session_id']:
                    print(f"  {key}: {metrics[key]}")
        else:
            print("\nMETRICS: None")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    inspect()

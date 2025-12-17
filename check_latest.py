import sqlite3
import os
import json

DB_PATH = "golf_analyzer.db"

def check_latest():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get latest session with feedback
    cursor.execute("""
        SELECT s.id, f.id, f.phase_feedback 
        FROM swing_sessions s 
        LEFT JOIN swing_feedback f ON s.id = f.session_id 
        ORDER BY s.created_at DESC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    
    if row:
        sid, fid, pf = row
        print(f"Latest Session ID: {sid}")
        print(f"Feedback ID: {fid}")
        print(f"Phase Feedback Raw: {pf[:100] if pf else 'None'}")
        
        if pf:
             try:
                 data = json.loads(pf) if isinstance(pf, str) else pf
                 print(f"Phase Feedback Keys: {list(data.keys())}")
             except:
                 print("Could not parse JSON")
    else:
        print("No sessions found")
        
    conn.close()

if __name__ == "__main__":
    check_latest()

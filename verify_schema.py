import sqlite3

def verify_schema():
    print("Verifying database schema...")
    conn = sqlite3.connect('golf_analyzer.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(swing_metrics)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columns in swing_metrics: {columns}")
        
        required = ['chest_turn_top_deg', 'pelvis_turn_top_deg']
        missing = [col for col in required if col not in columns]
        
        if not missing:
            print("SUCCESS: All required columns present.")
        else:
            print(f"FAILURE: Missing columns: {missing}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify_schema()

import sqlite3
import os

DB_PATH = "golf_analyzer.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    try:
        cursor.execute("SELECT phase_feedback FROM swing_feedback LIMIT 1")
        print("Column 'phase_feedback' already exists.")
    except sqlite3.OperationalError:
        print("Column 'phase_feedback' does not exist. Adding...")
        cursor.execute("ALTER TABLE swing_feedback ADD COLUMN phase_feedback JSON")
        conn.commit()
        print("Migration complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

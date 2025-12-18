"""
Simple migration script to add swing_path_index column to the database.
"""
import sqlite3
import os

DB_PATH = "golf_analyzer.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. It will be created on first run.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(swing_metrics)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "swing_path_index" in columns:
        print("Column 'swing_path_index' already exists. No migration needed.")
    else:
        cursor.execute("ALTER TABLE swing_metrics ADD COLUMN swing_path_index REAL")
        conn.commit()
        print("Successfully added 'swing_path_index' column!")
    
    conn.close()

if __name__ == "__main__":
    migrate()

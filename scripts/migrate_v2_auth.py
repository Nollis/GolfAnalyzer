
import sqlite3
import os

DB_PATH = "golf_analyzer.db"

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "auth_provider" in columns:
            print("✅ 'auth_provider' column already exists.")
        else:
            print("⏳ Adding 'auth_provider' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR DEFAULT 'local'")
            conn.commit()
            print("✅ Added 'auth_provider' column.")

        # Also check for credits table just in case (handled by create_all usually, but good to verify)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credits'")
        if not cursor.fetchone():
             print("ℹ️ 'credits' table missing. It should be created by app startup if models are registered.")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()

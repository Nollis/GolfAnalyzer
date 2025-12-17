import sqlite3
import os

DB_PATH = "golf_analyzer.db"

def check_user(email):
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check specific user
        print(f"Checking for user: {email}")
        cursor.execute("SELECT id, email, is_active FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user:
            print(f"User found: ID={user[0]}, Email={user[1]}, Active={user[2]}")
        else:
            print("User NOT found.")
            
        # Check total user count
        cursor.execute("SELECT count(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"Total users in database: {count}")
        
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        # List tables to see if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", [t[0] for t in tables])
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_user("hampusjbergh@icloud.com")

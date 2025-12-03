"""
Migration script to update database schema
"""
from app.core.database import Base, engine
from app.models.user import User
from app.models.db import SwingSession, SwingMetric, SwingPhase, SwingFeedbackDB, ReferenceProfileDB
from app.models.drill import Drill
import sqlite3

def migrate():
    print("Starting database migration...")
    
    # Create all tables using SQLAlchemy
    print("Creating/updating tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created/updated")
    
    # Add missing columns to existing tables
    conn = sqlite3.connect('golf_analyzer.db')
    cursor = conn.cursor()
    
    try:
        # Check and add skill_level to users table
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        if 'skill_level' not in user_columns:
            print("Adding skill_level column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN skill_level VARCHAR DEFAULT 'Beginner'")
            conn.commit()
            print("✓ Added skill_level column")
        else:
            print("✓ skill_level column already exists")
        
        # Check and add is_personal_best to swing_sessions table
        cursor.execute("PRAGMA table_info(swing_sessions)")
        session_columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_personal_best' not in session_columns:
            print("Adding is_personal_best column to swing_sessions table...")
            cursor.execute("ALTER TABLE swing_sessions ADD COLUMN is_personal_best BOOLEAN DEFAULT 0")
            conn.commit()
            print("✓ Added is_personal_best column")
        else:
            print("✓ is_personal_best column already exists")
        
        # Check and add user_id to swing_sessions table
        if 'user_id' not in session_columns:
            print("Adding user_id column to swing_sessions table...")
            cursor.execute("ALTER TABLE swing_sessions ADD COLUMN user_id VARCHAR")
            conn.commit()
            print("✓ Added user_id column")
        else:
            print("✓ user_id column already exists")
            
        # Check and add new metrics to swing_metrics table
        cursor.execute("PRAGMA table_info(swing_metrics)")
        metric_columns = [col[1] for col in cursor.fetchall()]
        
        new_metrics = [
            'chest_turn_top_deg', 'pelvis_turn_top_deg', 'x_factor_top_deg',
            'spine_angle_address_deg', 'spine_angle_impact_deg',
            'lead_arm_address_deg', 'lead_arm_top_deg', 'lead_arm_impact_deg',
            'trail_elbow_address_deg', 'trail_elbow_top_deg', 'trail_elbow_impact_deg',
            'knee_flex_left_address_deg', 'knee_flex_right_address_deg',
            'head_sway_range', 'early_extension_amount'
        ]
        
        for metric in new_metrics:
            if metric not in metric_columns:
                print(f"Adding {metric} column to swing_metrics table...")
                cursor.execute(f"ALTER TABLE swing_metrics ADD COLUMN {metric} FLOAT")
                conn.commit()
                print(f"✓ Added {metric} column")
            else:
                print(f"✓ {metric} column already exists")
            
    except Exception as e:
        print(f"Note: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("1. Run: python create_admin.py")
    print("2. Run: python -m app.core.seed_drills")
    print("3. Restart backend: uvicorn app.main:app --reload")

if __name__ == "__main__":
    migrate()

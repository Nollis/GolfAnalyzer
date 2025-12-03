import sqlite3

def fix_schema():
    print("Fixing database schema...")
    conn = sqlite3.connect('golf_analyzer.db')
    cursor = conn.cursor()
    
    new_metrics = [
        'chest_turn_top_deg', 'pelvis_turn_top_deg', 'x_factor_top_deg',
        'spine_angle_address_deg', 'spine_angle_impact_deg',
        'lead_arm_address_deg', 'lead_arm_top_deg', 'lead_arm_impact_deg',
        'trail_elbow_address_deg', 'trail_elbow_top_deg', 'trail_elbow_impact_deg',
        'knee_flex_left_address_deg', 'knee_flex_right_address_deg',
        'head_sway_range', 'early_extension_amount'
    ]
    
    try:
        cursor.execute("PRAGMA table_info(swing_metrics)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        for metric in new_metrics:
            if metric not in existing_columns:
                print(f"Adding {metric}...")
                try:
                    cursor.execute(f"ALTER TABLE swing_metrics ADD COLUMN {metric} FLOAT")
                    conn.commit()
                    print(f"✓ Added {metric}")
                except Exception as e:
                    print(f"Error adding {metric}: {e}")
            else:
                print(f"✓ {metric} already exists")
                
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        conn.close()
        print("Done.")

if __name__ == "__main__":
    fix_schema()

"""
Migration script to add new metric columns to the database.
Run this once to update the schema.
"""
import sqlite3
import os

DB_PATH = "golf_analyzer.db"

NEW_COLUMNS = [
    ("hand_height_at_top_index", "REAL"),
    ("hand_width_at_top_index", "REAL"),
    ("head_drop_cm", "REAL"),
    ("head_rise_cm", "REAL"),
    
    # Extended MHR Metrics
    ("finish_balance", "REAL"),
    
    # Sway
    ("pelvis_sway_top_cm", "REAL"),
    ("pelvis_sway_impact_cm", "REAL"),
    ("pelvis_sway_finish_cm", "REAL"),
    ("shoulder_sway_top_cm", "REAL"),
    ("shoulder_sway_impact_cm", "REAL"),
    ("shoulder_sway_finish_cm", "REAL"),
    ("pelvis_sway_range_cm", "REAL"),
    ("shoulder_sway_range_cm", "REAL"),

    # Swing Plane
    ("swing_plane_top_deg", "REAL"),
    ("swing_plane_impact_deg", "REAL"),
    ("swing_plane_deviation_top_deg", "REAL"),
    ("swing_plane_deviation_impact_deg", "REAL"),
    ("swing_plane_shift_top_to_impact_deg", "REAL"),
    ("arm_above_plane_at_top", "INTEGER"), # Boolean is INTEGER in SQLite

    # Finish & Head Recovery
    ("spine_angle_finish_deg", "REAL"),
    ("spine_angle_top_deg", "REAL"),
    ("extension_from_address_deg", "REAL"),
    ("chest_turn_finish_deg", "REAL"),
    ("pelvis_turn_finish_deg", "REAL"),
    ("head_rise_top_to_finish_cm", "REAL"),
    ("head_lateral_shift_address_to_finish_cm", "REAL"),
    
    # Hand Finish
    ("hand_height_finish_norm", "REAL"),
    ("hand_depth_finish_norm", "REAL"),
    ("hand_height_finish_label", "TEXT"),
    ("hand_depth_finish_label", "TEXT"),
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(swing_metrics)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing_columns:
            print(f"Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE swing_metrics ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column {col_name} already exists, skipping")
    
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()

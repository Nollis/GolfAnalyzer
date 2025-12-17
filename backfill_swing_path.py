
import os
import sys
import json
import sqlite3
from typing import List, Dict, Any

# Ensure we can import app modules
sys.path.append(os.getcwd())

from pose.metrics import MetricsCalculator, _get_xyz_from_frame, IDX_L_WRIST, IDX_R_WRIST, IDX_L_SHOULDER, IDX_R_SHOULDER
from app.models.db import SwingSession, SwingMetric
from app.schemas import SwingPhases, SwingMetrics
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = "golf_analyzer.db"

def get_latest_session_id():
    # Find the most recently modified poses.json file
    poses_files = [f for f in os.listdir("videos") if f.endswith("_poses.json")]
    if not poses_files:
        return None
    
    latest_file = max(poses_files, key=lambda f: os.path.getmtime(os.path.join("videos", f)))
    # Filename is {uuid}_poses.json
    return latest_file.replace("_poses.json", "")

def backfill():
    session_id = get_latest_session_id()
    if not session_id:
        print("No sessions found.")
        return

    print(f"Backfilling Swing Path for Session: {session_id}")
    
    # Load Pose Data
    pose_file = os.path.join("videos", f"{session_id}_poses.json")
    if not os.path.exists(pose_file):
        print(f"Pose file {pose_file} not found.")
        return
        
    with open(pose_file, "r") as f:
        pose_data = json.load(f)
        
    frames = pose_data.get("frames", [])
    phases_dict = pose_data.get("phases", {})
    
    top_frame_idx = phases_dict.get("top_frame")
    impact_frame_idx = phases_dict.get("impact_frame")
    
    if top_frame_idx is None or impact_frame_idx is None:
        print("Missing Top or Impact phase.")
        return

    # Calculate Swing Path Index
    calculator = MetricsCalculator()
    
    # Calculate using the internal method
    swing_path_index = calculator._compute_swing_path_index(
        frames,
        top_frame_idx,
        impact_frame_idx,
        handedness="Right" # Assumed for now
    )
    
    print(f"Calculated Swing Path Index: {swing_path_index}")
    
    # Update Database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE swing_metrics SET swing_path_index = ? WHERE session_id = ?",
        (swing_path_index, session_id)
    )
    conn.commit()
    conn.close()
    
    print("Database updated successfully!")

if __name__ == "__main__":
    backfill()

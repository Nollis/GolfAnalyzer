from app.core.database import SessionLocal
from app.models.drill import Drill

def seed_drills():
    db = SessionLocal()
    
    # List of drills to seed
    drills_data = [
        # --- TEMPO & TIMING ---
        {
            "title": "3:1 Tempo Drill",
            "description": "Master the tour-proven 3:1 tempo ratio. count '1-2-3' on the backswing and '1' on the downswing impact. Use a metronome app set to 45-50 BPM for the backswing start.",
            "category": "Tempo",
            "difficulty": "All Levels",
            "target_metric": "tempo_ratio",
            "video_url": None
        },
        {
            "title": "Pause at the Top",
            "description": "Swing to the top, pause for a full 2 seconds to ensure complete rotation and balance, then swing down aggressively. Cures rushed transitions.",
            "category": "Tempo",
            "difficulty": "Intermediate",
            "target_metric": "tempo_ratio",
            "video_url": None
        },
        {
            "title": "Feet Together Drill",
            "description": "Hit shots with feet completely together. This forces better tempo and balance, as you cannot rely on swaying or aggressive lateral driving.",
            "category": "Tempo",
            "difficulty": "Beginner",
            "target_metric": "finish_balance",
            "video_url": None
        },

        # --- ROTATION (Backswing) ---
        {
            "title": "Cross-Arm Chest Turn",
            "description": "Hold a club across your shoulders. Rotate until the grip end points at the ball (or past it) on the backswing. Ensure your hips turn 45 degrees.",
            "category": "Rotation",
            "difficulty": "Beginner",
            "target_metric": "chest_turn_top_deg",
            "video_url": None
        },
        {
            "title": "Wall Butt Drill (Rotation)",
            "description": "Set up with your butt against a wall. Make a backswing keeping your right cheek on the wall. On downswing, transition to left cheek. Ensures proper hip depth.",
            "category": "Rotation",
            "difficulty": "Intermediate",
            "target_metric": "hip_turn_top_deg",
            "video_url": None
        },
        {
            "title": "Reverse X-Factor Stretch",
            "description": "Sit on a chair (fixing hips). Rotate your torso as far as possible to the right. Hold for stretch. Increases thoracic mobility for X-Factor.",
            "category": "Rotation",
            "difficulty": "Advanced",
            "target_metric": "x_factor_top_deg",
            "video_url": None
        },
        {
            "title": "Right Foot Drop Back",
            "description": "Stagger your stance by pulling your right foot back 1-2 feet. This opens the hips and allows for easier/deeper rotation on the backswing.",
            "category": "Rotation",
            "difficulty": "Beginner",
            "target_metric": "pelvis_turn_top_deg",
            "video_url": None
        },
        
        # --- POSTURE & BALANCE ---
        {
            "title": "Wall Head Drill",
            "description": "Rest your forehead against a wall (or foam noodle). Make backswings without your head leaving the wall or sliding along it. Fixes swaying.",
            "category": "Posture",
            "difficulty": "Beginner",
            "target_metric": "head_sway_range",
            "video_url": None
        },
        {
            "title": "Chair Squat Drill",
            "description": "Place a chair behind you. At setup, hover just off it. As you swing, maintain that 'sitting' posture. Prevents early extension (standing up).",
            "category": "Posture",
            "difficulty": "Intermediate",
            "target_metric": "early_extension_amount",
            "video_url": None
        },
        {
            "title": "Flamingo Drill",
            "description": "Stand on your lead leg only, with trail leg toe touching the ground for balance. Make small swings. Forces perfect weight transfer and balance.",
            "category": "Balance",
            "difficulty": "Advanced",
            "target_metric": "finish_balance",
            "video_url": None
        },
         {
            "title": "Spine Angle Maintenance",
            "description": "Video yourself down-the-line. Draw a line on your spine. Swing staying on that line. If you rise up, you lose power and consistency.",
            "category": "Posture",
            "difficulty": "Intermediate",
            "target_metric": "spine_angle_impact_deg",
            "video_url": None
        },

        # --- ARM STRUCTURE ---
        {
            "title": "Towel Drill",
            "description": "Place a towel under both armpits. Make half-swings without dropping the towel. Keeps arms connected to the torso (sync).",
            "category": "Arm Structure",
            "difficulty": "Beginner",
            "target_metric": "lead_arm_impact_deg",
            "video_url": None
        },
        {
            "title": "Straight Arm Extension",
            "description": "Focus on keeping the lead arm straight well past impact. Feel like you are shaking hands with the target. Prevents 'chicken wing'.",
            "category": "Arm Structure",
            "difficulty": "Beginner",
            "target_metric": "lead_arm_impact_deg",
            "video_url": None
        },
        {
            "title": "Waiter's Tray Drill",
            "description": "At the top of the backswing, feel like your right hand is holding a tray of drinks (palm up). Fixes flying right elbow.",
            "category": "Arm Structure",
            "difficulty": "Intermediate",
            "target_metric": "trail_elbow_top_deg",
            "video_url": None
        },

        # --- WRISTS & IMPACT ---
        {
            "title": "Impact Bag",
            "description": "Hit an impact bag (or old pillow). Stop at impact. Check that lead wrist is flat or bowed, hands are ahead of clubhead (shaft lean).",
            "category": "Impact",
            "difficulty": "All Levels",
            "target_metric": "shaft_lean_impact_deg",
            "video_url": None
        },
        {
            "title": "Ruler Drill",
            "description": "Tuck a ruler into your lead glove on the top of your wrist. If you 'cup' or 'flip' firmly, the ruler will dig into your forearm. Keep structure.",
            "category": "Wrist Angles",
            "difficulty": "Intermediate",
            "target_metric": "lead_wrist_flexion_impact_deg",
            "video_url": None
        },
        {
            "title": "Pump Drill",
            "description": "Go to top. 'Pump' the club down halfway twice, retaining wrist lag angle. On third pump, hit the ball. Teaches lag retention.",
            "category": "Impact",
            "difficulty": "Advanced",
            "target_metric": "lead_wrist_hinge_top_deg",
            "video_url": None
        },
        
        # --- PATH & PLANE ---
        {
            "title": "Gate Drill (Putting/Chipping)",
            "description": "Place two tees just outside your putter head width. Stroke through the gate without hitting tees. Improves center contact.",
            "category": "Path",
            "difficulty": "Beginner",
            "target_metric": "swing_path_index",
            "video_url": None
        },
         {
            "title": "Headcover Drill (Slice Fix)",
            "description": "Place a headcover just outside the ball (far side). Swing inside-out to avoid hitting it. Forces an in-to-out path to cure slices.",
            "category": "Path",
            "difficulty": "Intermediate",
            "target_metric": "swing_path_index",
            "video_url": None
        },
        {
            "title": "Alignment Stick Plane Guide",
            "description": "Stick an alignment rod into the ground at the same angle as your club shaft, 3 feet behind you. Swing under/along it, not over it.",
            "category": "Path",
            "difficulty": "Advanced",
            "target_metric": "hand_height_at_top_index",
            "video_url": None
        }
    ]

    print(f"Seeding {len(drills_data)} drills...")
    
    # Check existing to avoid duplicates
    existing_titles = {d.title for d in db.query(Drill).all()}
    
    added_count = 0
    for drill_data in drills_data:
        if drill_data["title"] in existing_titles:
            print(f"Skipping existing: {drill_data['title']}")
            continue
            
        drill = Drill(**drill_data)
        db.add(drill)
        added_count += 1
        
    db.commit()
    print(f"Successfully added {added_count} new drills!")
    db.close()

if __name__ == "__main__":
    seed_drills()

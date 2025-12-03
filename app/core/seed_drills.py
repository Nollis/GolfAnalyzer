from app.core.database import SessionLocal
from app.models.drill import Drill

DRILLS_DATA = [
    {
        "title": "Tempo Drill: 3:1 Ratio",
        "description": "Practice your swing tempo by counting '1-2-3' on the backswing and '1' on the downswing. This helps achieve the ideal 3:1 tempo ratio.",
        "category": "Tempo",
        "difficulty": "Beginner",
        "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ", # Placeholder
        "target_metric": "tempo_ratio"
    },
    {
        "title": "Shoulder Turn Wall Drill",
        "description": "Stand with your back to a wall. Simulate a backswing and try to touch the wall with your lead shoulder. This ensures a full 90-degree shoulder turn.",
        "category": "Rotation",
        "difficulty": "Intermediate",
        "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "target_metric": "shoulder_turn_top_deg"
    },
    {
        "title": "Hip Turn Chair Drill",
        "description": "Place a chair behind you. On the backswing, your trail hip should not bump the chair, but rotate inside it. On the downswing, your lead hip should clear the chair.",
        "category": "Rotation",
        "difficulty": "Advanced",
        "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "target_metric": "hip_turn_top_deg"
    },
    {
        "title": "Pause at the Top",
        "description": "Swing to the top and pause for 2 seconds before starting the downswing. This helps prevent rushing and improves transition sequencing.",
        "category": "Tempo",
        "difficulty": "Intermediate",
        "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "target_metric": "tempo_ratio"
    }
]

def seed_drills():
    db = SessionLocal()
    try:
        # Check if drills exist
        existing_count = db.query(Drill).count()
        if existing_count > 0:
            print(f"Drills already seeded ({existing_count} found). Skipping.")
            return

        print("Seeding drills...")
        for drill_data in DRILLS_DATA:
            drill = Drill(**drill_data)
            db.add(drill)
        
        db.commit()
        print(f"Successfully seeded {len(DRILLS_DATA)} drills.")
        
    except Exception as e:
        print(f"Error seeding drills: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_drills()

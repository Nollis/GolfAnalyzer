from app.core.database import SessionLocal
from app.models.drill import Drill

db = SessionLocal()
count = db.query(Drill).count()
print(f"Drill count: {count}")
drills = db.query(Drill).all()
for d in drills:
    print(f"- {d.title} ({d.category})")
db.close()

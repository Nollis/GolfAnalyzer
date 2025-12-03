from sqlalchemy import Column, Integer, String, Float, Enum
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Drill(Base):
    __tablename__ = "drills"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False) # e.g., "Tempo", "Rotation", "Setup"
    difficulty = Column(String, default="Beginner") # Beginner, Intermediate, Advanced
    video_url = Column(String, nullable=True)
    target_metric = Column(String, nullable=True) # e.g., "tempo_ratio", "shoulder_turn_top_deg"

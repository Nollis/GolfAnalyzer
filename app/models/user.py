from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # Nullable for OAuth users
    auth_provider = Column(String, default="local") # local, google, apple
    full_name = Column(String)
    handicap = Column(Float, default=0.0)
    skill_level = Column(String, default="Beginner") # Beginner, Intermediate, Advanced, Pro
    handedness = Column(String, default="right")
    height_cm = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # Relationships
    sessions = relationship("SwingSession", back_populates="user")
    credits = relationship("Credits", uselist=False, back_populates="user")

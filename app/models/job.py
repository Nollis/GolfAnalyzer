"""
Analysis Job model for tracking video processing jobs.

Supports local development and cloud deployment with queue-based processing.
"""
from sqlalchemy import Column, String, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobStatus(str, enum.Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(Base):
    """Database model for analysis jobs."""
    __tablename__ = "analysis_jobs"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    
    # Job status
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0)
    current_step = Column(String(255), default="Queued")
    error_message = Column(Text, nullable=True)
    
    # Input parameters
    video_path = Column(String(512), nullable=False)
    handedness = Column(String(10), nullable=True)
    view = Column(String(20), nullable=False)
    club_type = Column(String(50), nullable=True)
    
    # Result reference (links to SwingSession when complete)
    session_id = Column(String(36), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Processing metadata
    pose_method = Column(String(50), nullable=True)  # "HybrIK 3D" or "MediaPipe 2D"
    processing_time_ms = Column(Float, nullable=True)


# Pydantic schemas for API
class JobCreate(BaseModel):
    """Schema for creating a new job."""
    video_path: str
    handedness: Optional[str] = None
    view: str
    club_type: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Schema for job status response."""
    id: str
    status: JobStatus
    progress: float
    current_step: str
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    pose_method: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class JobQueueResponse(BaseModel):
    """Schema for queue job response."""
    job_id: str
    status: JobStatus
    message: str



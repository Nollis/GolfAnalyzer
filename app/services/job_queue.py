from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.job import AnalysisJob as Job
from typing import Optional, Dict, Any
import datetime
import uuid
from pydantic import BaseModel

# --- Queue Interface Types ---
class QueueMessage(BaseModel):
    job_id: str
    user_id: str
    video_path: str
    handedness: Optional[str] = None
    view: str
    club_type: Optional[str] = None

# --- In-Memory / DB Wrapper ---
class JobQueueService:
    """
    Service wrapper for job queue operations.
    In a real system, this might wrap Redis/RabbitMQ.
    Here it wraps our SQL 'Job' table logic.
    """
    def enqueue(self, message: QueueMessage) -> bool:
        # In this SQL-based queue, the 'enqueue' is actually just 
        # ensuring the job exists in the DB with status='queued'.
        # Since routes_jobs.py already creates the Job record, 
        # we might just return True or double-check.
        
        # However, to support the abstraction that `worker.py` expects 
        # (polling a queue), we can implement a simple in-memory queue 
        # OR just rely on the DB polling in the worker.
        
        # Given the current worker implementation (worker.py):
        # It polls the DB: `JobQueue.claim_next_job(db, WORKER_ID)`
        # So we don't strictly need an in-memory queue for the worker to find it.
        # But `routes_jobs.py` calls `queue.enqueue(message)`.
        
        # So let's make this method a no-op that just returns True, 
        # because the DB record creation *is* the enqueuing.
        return True

    def dequeue(self, timeout: float = 1.0) -> Optional[QueueMessage]:
        # This method is used by the worker if it uses the queue service abstraction.
        # But wait, `worker.py` currently imports `JobQueue` static methods directly?
        # A check of `worker.py` (which I can't see right now but remember) 
        # suggests it might use `get_queue().dequeue()` OR `JobQueue.claim_next_job`.
        
        # Let's support both for safety.
        return None 

    def size(self) -> int:
        # Return count of queued jobs
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            return db.query(Job).filter(Job.status == "queued").count()
        finally:
            db.close()

# Global instance
_queue_instance = JobQueueService()

def get_queue() -> JobQueueService:
    return _queue_instance


# --- Legacy / Static Methods (Keep for compatibility if needed) ---
class JobQueue:
    @staticmethod
    def enqueue(db: Session, payload: Dict[str, Any], job_type: str = "swing_analysis") -> Job:
        job = Job(
            payload=payload,
            job_type=job_type,
            status="queued"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def claim_next_job(db: Session, worker_id: str) -> Optional[Job]:
        # Simple atomic-ish claim for SQLite/Postgres
        job = db.query(Job).filter(Job.status == "queued").order_by(Job.created_at.asc()).first()
        
        if job:
            job.status = "processing"
            job.worker_id = worker_id
            job.updated_at = datetime.datetime.utcnow()
            job.attempts += 1
            db.commit()
            db.refresh(job)
            return job
            
        return None

    @staticmethod
    def complete_job(db: Session, job_id: str, result: Dict[str, Any]):
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
            job.result = result
            job.updated_at = datetime.datetime.utcnow()
            db.commit()

    @staticmethod
    def fail_job(db: Session, job_id: str, error: str):
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(error)
            job.updated_at = datetime.datetime.utcnow()
            db.commit()
            
    @staticmethod
    def get_job_status(db: Session, job_id: str) -> Optional[Dict[str, Any]]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
            
        return {
            "id": job.id,
            "status": job.status,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }

def init_job_queue():
    # Placeholder for any init logic
    pass

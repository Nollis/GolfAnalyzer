import time
import sys
import uuid
import logging
from app.core.database import SessionLocal
from app.services.job_queue import JobQueue
# Ensure models are loaded for SQLAlchemy registry
import app.models.user 
import app.models.db

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [WORKER] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

WORKER_ID = f"worker-local-{str(uuid.uuid4())[:8]}"

from app.services.analysis import run_analysis_pipeline
import os

def process_job(job):
    """
    Runs the analysis pipeline for the job.
    """
    logger.info(f"Processing Job {job.id} (Type: {job.job_type})")
    
    if job.job_type == "swing_analysis":
        payload = job.payload
        if not payload:
            raise ValueError("Empty payload")
            
        # Extract args
        # Extract args and resolve path via storage
        from app.core.storage import get_storage
        storage = get_storage()
        
        video_key = payload.get("video_key")
        video_path = None
        
        if video_key:
            try:
                video_path = storage.get_path(video_key)
            except Exception as e:
                raise ValueError(f"Failed to resolve local path for key {video_key}: {e}")
        else:
            # Legacy fallback
            video_path = payload.get("video_path")
            
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path} (Key: {video_key})")
            
        handedness = payload.get("handedness")
        view = payload.get("view")
        club_type = payload.get("club_type")
        user_id = payload.get("user_id")
        
        # We need a db session for the analysis logic
        db = SessionLocal()
        try:
            result = run_analysis_pipeline(
                video_path=video_path,
                handedness=handedness,
                view=view,
                club_type=club_type,
                user_id=user_id,
                db=db
            )
            return result
        finally:
            db.close()
            
    else:
        # Unknown job type
        logger.warning(f"Unknown job type: {job.job_type}")
        time.sleep(1) # simulate fast fail
        return {"status": "skipped", "reason": "unknown_type"}


def run_worker():
    logger.info(f"Starting Worker {WORKER_ID}...")
    logger.info("Polling for jobs... (Ctrl+C to stop)")
    
    while True:
        db = SessionLocal()
        try:
            job = JobQueue.claim_next_job(db, WORKER_ID)
            
            if job:
                try:
                    result = process_job(job)
                    JobQueue.complete_job(db, job.id, result)
                    logger.info(f"✅ Job {job.id} completed successfully.")
                except Exception as e:
                    logger.error(f"❌ Job {job.id} failed: {e}")
                    JobQueue.fail_job(db, job.id, str(e))
            else:
                # No jobs, sleep to avoid hammering DB
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
            time.sleep(5)
        finally:
            db.close()

if __name__ == "__main__":
    run_worker()

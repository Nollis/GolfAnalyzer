"""
Job management routes for async analysis processing.

Provides endpoints for:
- Queuing new analysis jobs
- Checking job status/progress
- Getting job results
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
import tempfile
import shutil
from pathlib import Path

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.job import AnalysisJob, JobStatus, JobStatusResponse, JobQueueResponse
from app.services.job_queue import get_queue, QueueMessage

router = APIRouter()


@router.post("/analyze", response_model=JobQueueResponse)
async def queue_analysis(
    video: UploadFile = File(...),
    handedness: Optional[str] = Form(None),
    view: str = Form(...),
    club_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Queue a video for analysis.
    
    Returns immediately with a job_id. Use GET /jobs/{job_id} to check status.
    
    This pattern allows:
    - Fast response times
    - Background processing
    - Progress tracking
    - Scalability to multiple workers
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded video to a persistent location
    video_dir = Path("videos")
    video_dir.mkdir(exist_ok=True)
    
    video_path = video_dir / f"{job_id}.mp4"
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)
    
    # Create job record in database
    job = AnalysisJob(
        id=job_id,
        user_id=str(current_user.id),
        status=JobStatus.PENDING,
        video_path=str(video_path),
        handedness=handedness,
        view=view,
        club_type=club_type,
        current_step="Queued",
        progress=0.0,
    )
    db.add(job)
    db.commit()
    
    # Add to processing queue
    queue = get_queue()
    message = QueueMessage(
        job_id=job_id,
        user_id=str(current_user.id),
        video_path=str(video_path),
        handedness=handedness,
        view=view,
        club_type=club_type,
    )
    
    success = queue.enqueue(message)
    if not success:
        # Queue full, mark job as failed
        job.status = JobStatus.FAILED
        job.error_message = "Server busy, please try again later"
        db.commit()
        raise HTTPException(status_code=503, detail="Server busy, please try again later")
    
    return JobQueueResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Video queued for analysis. Poll GET /api/v1/jobs/{job_id} for status."
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the status of an analysis job.
    
    Poll this endpoint to track progress. When status is "completed",
    the session_id field will contain the ID of the analysis results.
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.user_id == str(current_user.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse.from_orm(job)


@router.get("", response_model=List[JobStatusResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List user's analysis jobs.
    
    Optionally filter by status: pending, processing, completed, failed
    """
    query = db.query(AnalysisJob).filter(
        AnalysisJob.user_id == str(current_user.id)
    )
    
    if status:
        try:
            status_enum = JobStatus(status)
            query = query.filter(AnalysisJob.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    jobs = query.order_by(AnalysisJob.created_at.desc()).limit(limit).all()
    
    return [JobStatusResponse.from_orm(job) for job in jobs]


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a pending job.
    
    Only pending jobs can be cancelled. Processing jobs will complete.
    """
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.user_id == str(current_user.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job in {job.status.value} status"
        )
    
    job.status = JobStatus.FAILED
    job.error_message = "Cancelled by user"
    db.commit()
    
    # Clean up video file
    try:
        Path(job.video_path).unlink(missing_ok=True)
    except Exception:
        pass
    
    return {"message": "Job cancelled"}


@router.get("/queue/status")
async def get_queue_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current queue status.
    
    Returns queue size and worker status.
    """
    from app.services.job_queue import get_queue
    from app.workers.analysis_worker import get_worker
    
    queue = get_queue()
    worker = get_worker()
    
    return {
        "queue_size": queue.size(),
        "worker_running": worker.is_running(),
    }



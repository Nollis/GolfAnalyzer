from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Query
from app.schemas import AnalysisResponse, SwingPhases, SwingMetrics, SwingScores, SwingFeedback, SwingAnalysisRequest, MetricScore, DrillResponse, ReferenceProfileCreate, ReferenceProfileResponse, SessionSummaryResponse, SimpleScores

from pose.types import FramePose, Point3D
from pose.swing_detection import SwingDetector
from pose.metrics import MetricsCalculator
from pathlib import Path

# Try to import HybrIK
try:
    from pose.smpl_extractor import (
        get_hybrik_extractor,
        smpl_to_mediapipe_format,
        is_smpl_available,
        HYBRIK_AVAILABLE
    )
except ImportError:
    HYBRIK_AVAILABLE = False
from reference.reference_profiles import get_reference_profile_for, ReferenceProfile, MetricTarget
from reference.scoring import Scorer
from services.feedback_service import FeedbackService
import uuid
import tempfile
import shutil
import os
import json
import cv2
from sqlalchemy.orm import Session
from app.core.database import get_db, Base, engine
from fastapi import Depends
from app.services.analysis_repository import AnalysisRepository
from app.services.video_storage import VideoStorage
from app.core.storage import get_storage
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.db import SwingSession
from typing import List, Optional
from fastapi.responses import FileResponse, StreamingResponse
from app.services.report_service import ReportService

# Create tables on startup (for dev simplicity)
Base.metadata.create_all(bind=engine)


def _get_feedback_from_db(feedback_db) -> SwingFeedback:
    """Convert database feedback to SwingFeedback schema, handling None.
       Handles migration of legacy drill data (missing IDs/categories).
    """
    if feedback_db:
        drills = []
        raw_drills = feedback_db.drills if feedback_db.drills else []
        for d in raw_drills:
            # Handle legacy drills that lack ID/Category
            if "id" not in d:
                d["id"] = "legacy-drill"
            if "category" not in d:
                d["category"] = "General"
            
            try:
                drills.append(DrillResponse(**d))
            except Exception:
                # If validation still fails, skip or insert minimal placeholder
                continue

        return SwingFeedback(
            summary=feedback_db.summary,
            priority_issues=feedback_db.priority_issues if feedback_db.priority_issues else [],
            drills=drills,
            phase_feedback=feedback_db.phase_feedback if feedback_db.phase_feedback else {}
        )
    else:
        return SwingFeedback(
            summary="Feedback generation was disabled for this analysis.",
            priority_issues=[],
            drills=[],
            phase_feedback={}
        )


router = APIRouter()

from app.services.job_queue import JobQueue
from app.core.storage import get_storage
from typing import Dict, Any

@router.post("/jobs/analyze", summary="Async Swing Analysis", tags=["jobs"])
async def analyze_swing_async(
    video: UploadFile = File(...),
    handedness: Optional[str] = Form(None),
    view: str = Form(...),
    club_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submits a swing analysis job to the queue.
    Returns a job_id immediately.
    """
    # 1. Save File to persistent storage using Storage Abstraction
    # "uploads" prefix is logical key grouping
    file_id = str(uuid.uuid4())
    ext = Path(video.filename).suffix or ".mp4"
    key = f"uploads/{file_id}{ext}"
    
    try:
        storage = get_storage()
        storage.save(video.file, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
        
    # 2. Enqueue Job
    payload = {
        "video_key": key,
        "handedness": handedness,
        "view": view,
        "club_type": club_type,
        "user_id": current_user.id
    }
    
    job = JobQueue.enqueue(db, payload, job_type="swing_analysis")
    
    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Analysis queued successfully. Poll /jobs/{job_id} for results."
    }

@router.get("/jobs/{job_id}", summary="Get Job Status", tags=["jobs"])
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    status = JobQueue.get_job_status(db, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return status

# Legacy Synchronous Endpoint (kept for compatibility, calls internal service directly)
# NOTE: In a real migration, this might also just enqueue and wait.
@router.post("/analyze-swing", response_model=AnalysisResponse, 
              summary="Analyze swing (synchronous - DEPRECATED)",
              description="Deprecated. Use POST /jobs/analyze for async processing.")
async def analyze_swing(
    video: UploadFile = File(...),
    handedness: Optional[str] = Form(None),
    view: str = Form(...),
    club_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # For backward compat, we reuse the service logic synchronously
    from app.services.analysis import run_analysis_pipeline
    
    # Save temp
    suffix = ".mp4" 
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name
        
    try:
        # Run pipeline directly (blocking)
        result = run_analysis_pipeline(
            video_path=tmp_path,
            handedness=handedness,
            view=view,
            club_type=club_type,
            user_id=current_user.id,
            db=db
        )
        
        # To return the full AnalysisResponse, we need to fetch it from DB
        repo = AnalysisRepository(db)
        s = repo.get_session(result["session_id"])
        
        return _map_session_to_response(s)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _map_session_to_response(s: SwingSession) -> AnalysisResponse:
    """Helper to map a DB SwingSession to Value Object Schema"""
    m = s.metrics
    
    # Safely get attribute helper
    def get_val(obj, key):
        return getattr(obj, key, None)
        
    metrics = SwingMetrics(
        tempo_ratio=m.tempo_ratio,
        backswing_duration_ms=m.backswing_duration_ms,
        downswing_duration_ms=m.downswing_duration_ms,
        
        # Core & MHR metrics
        chest_turn_top_deg=get_val(m, 'chest_turn_top_deg'),
        pelvis_turn_top_deg=get_val(m, 'pelvis_turn_top_deg'),
        x_factor_top_deg=get_val(m, 'x_factor_top_deg'),
        spine_angle_address_deg=get_val(m, 'spine_angle_address_deg'),
        spine_angle_impact_deg=get_val(m, 'spine_angle_impact_deg'),
        lead_arm_address_deg=get_val(m, 'lead_arm_address_deg'),
        lead_arm_top_deg=get_val(m, 'lead_arm_top_deg'),
        lead_arm_impact_deg=get_val(m, 'lead_arm_impact_deg'),
        trail_elbow_address_deg=get_val(m, 'trail_elbow_address_deg'),
        trail_elbow_top_deg=get_val(m, 'trail_elbow_top_deg'),
        trail_elbow_impact_deg=get_val(m, 'trail_elbow_impact_deg'),
        knee_flex_left_address_deg=get_val(m, 'knee_flex_left_address_deg'),
        knee_flex_right_address_deg=get_val(m, 'knee_flex_right_address_deg'),
        head_sway_range=get_val(m, 'head_sway_range'),
        early_extension_amount=get_val(m, 'early_extension_amount'),
        swing_path_index=get_val(m, 'swing_path_index'),
        hand_height_at_top_index=get_val(m, 'hand_height_at_top_index'),
        hand_width_at_top_index=get_val(m, 'hand_width_at_top_index'),
        head_drop_cm=get_val(m, 'head_drop_cm'),
        head_rise_cm=get_val(m, 'head_rise_cm'),
        
        # Extended MHR
        finish_balance=get_val(m, 'finish_balance'),
        chest_turn_finish_deg=get_val(m, 'chest_turn_finish_deg'),
        pelvis_turn_finish_deg=get_val(m, 'pelvis_turn_finish_deg'),
        spine_angle_top_deg=get_val(m, 'spine_angle_top_deg'),
        spine_angle_finish_deg=get_val(m, 'spine_angle_finish_deg'),
        extension_from_address_deg=get_val(m, 'extension_from_address_deg'),
        head_rise_top_to_finish_cm=get_val(m, 'head_rise_top_to_finish_cm'),
        head_lateral_shift_address_to_finish_cm=get_val(m, 'head_lateral_shift_address_to_finish_cm'),
        hand_height_finish_norm=get_val(m, 'hand_height_finish_norm'),
        hand_depth_finish_norm=get_val(m, 'hand_depth_finish_norm'),
        pelvis_sway_top_cm=get_val(m, 'pelvis_sway_top_cm'),
        pelvis_sway_impact_cm=get_val(m, 'pelvis_sway_impact_cm'),
        pelvis_sway_finish_cm=get_val(m, 'pelvis_sway_finish_cm'),
        pelvis_sway_range_cm=get_val(m, 'pelvis_sway_range_cm'),
        shoulder_sway_top_cm=get_val(m, 'shoulder_sway_top_cm'),
        shoulder_sway_impact_cm=get_val(m, 'shoulder_sway_impact_cm'),
        shoulder_sway_finish_cm=get_val(m, 'shoulder_sway_finish_cm'),
        shoulder_sway_range_cm=get_val(m, 'shoulder_sway_range_cm'),
        swing_plane_top_deg=get_val(m, 'swing_plane_top_deg'),
        swing_plane_impact_deg=get_val(m, 'swing_plane_impact_deg'),
        swing_plane_deviation_top_deg=get_val(m, 'swing_plane_deviation_top_deg'),
        swing_plane_deviation_impact_deg=get_val(m, 'swing_plane_deviation_impact_deg'),
        swing_plane_shift_top_to_impact_deg=get_val(m, 'swing_plane_shift_top_to_impact_deg'),
        arm_above_plane_at_top=get_val(m, 'arm_above_plane_at_top'),
        
        # Backward compatibility
        shoulder_turn_top_deg=get_val(m, 'shoulder_turn_top_deg'),
        hip_turn_top_deg=get_val(m, 'hip_turn_top_deg'),
        spine_tilt_address_deg=get_val(m, 'spine_tilt_address_deg'),
        spine_tilt_impact_deg=get_val(m, 'spine_tilt_impact_deg'),
        head_movement_forward_cm=get_val(m, 'head_movement_forward_cm'),
        head_movement_vertical_cm=get_val(m, 'head_movement_vertical_cm'),
        shaft_lean_impact_deg=get_val(m, 'shaft_lean_impact_deg'),
        lead_wrist_flexion_address_deg=get_val(m, 'lead_wrist_flexion_address_deg'),
        lead_wrist_flexion_top_deg=get_val(m, 'lead_wrist_flexion_top_deg'),
        lead_wrist_flexion_impact_deg=get_val(m, 'lead_wrist_flexion_impact_deg'),
        lead_wrist_hinge_top_deg=get_val(m, 'lead_wrist_hinge_top_deg')
    )
    
    # Load MHR extended metrics from JSON if needed? 
    # NOTE: The job/service already populates most of these into DB columns if columns exist.
    # If columns don't exist, we'd need to load JSON.
    # For now, we assume the SwingMetrics logic in list_sessions catches them.
    # But wait, logic in list_sessions loads from columns.
    # The service updates columns.
    # So we should be good if columns exist.
    
    
    from reference.reference_profiles import get_reference_profile_for
    from reference.scoring import Scorer
    
    ref = get_reference_profile_for(s.club_type, s.view)
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref)
    
    feedback = _get_feedback_from_db(s.feedback)
    
    phases = SwingPhases(
        address_frame=s.phases.address_frame,
        top_frame=s.phases.top_frame,
        impact_frame=s.phases.impact_frame,
        finish_frame=s.phases.finish_frame
    )
    
    return AnalysisResponse(
        session_id=s.id,
        video_url=get_storage().get_url(s.video_url) if s.video_url else None,
        is_personal_best=s.is_personal_best,
        metadata=SwingAnalysisRequest(
            handedness=s.handedness,
            view=s.view,
            club_type=s.club_type
        ),
        phases=phases,
        metrics=metrics,
        scores=scores,
        feedback=feedback,
        created_at=s.created_at
    )


@router.get("/sessions", response_model=List[SessionSummaryResponse])
def list_sessions(
    skip: int = 0,
    limit: int = 50, 
    view: Optional[str] = None,
    club_type: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    # Filter by user
    query = db.query(SwingSession).filter(SwingSession.user_id == current_user.id)
    
    if view:
        query = query.filter(SwingSession.view == view)
    if club_type:
        query = query.filter(SwingSession.club_type == club_type)
        
    sessions = query.order_by(SwingSession.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for s in sessions:
        # Optimization: Don't load full metrics/feedback. Just Summary.
        # overall_score is stored directly on SwingSession class in db.py
        
        results.append(SessionSummaryResponse(
            session_id=s.id,
            scores=SimpleScores(overall_score=s.overall_score),
            metadata=SwingAnalysisRequest(
                handedness=s.handedness,
                view=s.view,
                club_type=s.club_type
            ),
            is_personal_best=s.is_personal_best,
            created_at=s.created_at
        ))
        
    return results


@router.get("/sessions/{session_id}", response_model=AnalysisResponse)
def get_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check ownership
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")
        
    # Map to response (Same logic as above - ideally refactor to a mapper function)
    m = s.metrics
    metrics = SwingMetrics(
        tempo_ratio=m.tempo_ratio,
        backswing_duration_ms=m.backswing_duration_ms,
        downswing_duration_ms=m.downswing_duration_ms,
        # New metrics (10 core metrics)
        chest_turn_top_deg=getattr(m, 'chest_turn_top_deg', None),
        pelvis_turn_top_deg=getattr(m, 'pelvis_turn_top_deg', None),
        x_factor_top_deg=getattr(m, 'x_factor_top_deg', None),
        spine_angle_address_deg=getattr(m, 'spine_angle_address_deg', None),
        spine_angle_impact_deg=getattr(m, 'spine_angle_impact_deg', None),
        lead_arm_address_deg=getattr(m, 'lead_arm_address_deg', None),
        lead_arm_top_deg=getattr(m, 'lead_arm_top_deg', None),
        lead_arm_impact_deg=getattr(m, 'lead_arm_impact_deg', None),
        trail_elbow_address_deg=getattr(m, 'trail_elbow_address_deg', None),
        trail_elbow_top_deg=getattr(m, 'trail_elbow_top_deg', None),
        trail_elbow_impact_deg=getattr(m, 'trail_elbow_impact_deg', None),
        knee_flex_left_address_deg=getattr(m, 'knee_flex_left_address_deg', None),
        knee_flex_right_address_deg=getattr(m, 'knee_flex_right_address_deg', None),
        head_sway_range=getattr(m, 'head_sway_range', None),
        early_extension_amount=getattr(m, 'early_extension_amount', None),
        swing_path_index=getattr(m, 'swing_path_index', None),
        hand_height_at_top_index=getattr(m, 'hand_height_at_top_index', None),
        hand_width_at_top_index=getattr(m, 'hand_width_at_top_index', None),
        head_drop_cm=getattr(m, 'head_drop_cm', None),
        head_rise_cm=getattr(m, 'head_rise_cm', None),
        # Backward compatibility (old field names)
        shoulder_turn_top_deg=getattr(m, 'shoulder_turn_top_deg', None),
        hip_turn_top_deg=getattr(m, 'hip_turn_top_deg', None),
        spine_tilt_address_deg=getattr(m, 'spine_tilt_address_deg', None),
        spine_tilt_impact_deg=getattr(m, 'spine_tilt_impact_deg', None),
        head_movement_forward_cm=getattr(m, 'head_movement_forward_cm', None),
        head_movement_vertical_cm=getattr(m, 'head_movement_vertical_cm', None),
        shaft_lean_impact_deg=getattr(m, 'shaft_lean_impact_deg', None),
        lead_wrist_flexion_address_deg=getattr(m, 'lead_wrist_flexion_address_deg', None),
        lead_wrist_flexion_top_deg=getattr(m, 'lead_wrist_flexion_top_deg', None),
        lead_wrist_flexion_impact_deg=getattr(m, 'lead_wrist_flexion_impact_deg', None),
        lead_wrist_hinge_top_deg=getattr(m, 'lead_wrist_hinge_top_deg', None)
    )
    
    # Load extended metrics from MHR JSON if available
    mhr_path = os.path.join("videos", f"{session_id}_mhr.json")
    if os.path.exists(mhr_path):
        try:
            with open(mhr_path, "r") as f:
                mhr_data = json.load(f)
            
            ext = mhr_data.get("extended_metrics", {})
            if ext:
                # Update metrics with extended values
                loaded = []
                for key, value in ext.items():
                    if hasattr(metrics, key) and value is not None:
                        setattr(metrics, key, value)
                        loaded.append(key)
                print(f"[get_session] Loaded {len(loaded)} extended metrics: {loaded[:5]}...")
        except Exception as e:
            print(f"[get_session] Failed to load MHR extended metrics: {e}")
    
    from reference.reference_profiles import get_reference_profile_for
    from reference.scoring import Scorer
    
    ref = get_reference_profile_for(s.club_type, s.view)
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref)
    
    feedback = _get_feedback_from_db(s.feedback)
    
    phases = SwingPhases(
        address_frame=s.phases.address_frame,
        top_frame=s.phases.top_frame,
        impact_frame=s.phases.impact_frame,
        finish_frame=s.phases.finish_frame
    )

    return AnalysisResponse(
        session_id=s.id,
        video_url=f"/api/v1/sessions/{s.id}/video" if s.video_url else None,
        is_personal_best=s.is_personal_best,
        metadata=SwingAnalysisRequest(
            handedness=s.handedness,
            view=s.view,
            club_type=s.club_type
        ),
        phases=phases,
        metrics=metrics,
        scores=scores,
        feedback=feedback,
        created_at=s.created_at
    )


@router.get("/personal-best", response_model=Optional[AnalysisResponse])
def get_personal_best(club_type: str, view: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    try:
        # Filter by user
        s = db.query(SwingSession).filter(
            SwingSession.user_id == current_user.id,
            SwingSession.club_type == club_type,
            SwingSession.view == view,
            SwingSession.is_personal_best == True
        ).first()
        
        if not s:
            return None
    except Exception as e:
        print(f"Error fetching personal best: {e}")
        return None
        
    # Reuse the mapping logic (ideally refactor this duplication)
    m = s.metrics
    metrics = SwingMetrics(
        tempo_ratio=m.tempo_ratio,
        backswing_duration_ms=m.backswing_duration_ms,
        downswing_duration_ms=m.downswing_duration_ms,
        # New metrics (10 core metrics)
        chest_turn_top_deg=getattr(m, 'chest_turn_top_deg', None),
        pelvis_turn_top_deg=getattr(m, 'pelvis_turn_top_deg', None),
        x_factor_top_deg=getattr(m, 'x_factor_top_deg', None),
        spine_angle_address_deg=getattr(m, 'spine_angle_address_deg', None),
        spine_angle_impact_deg=getattr(m, 'spine_angle_impact_deg', None),
        lead_arm_address_deg=getattr(m, 'lead_arm_address_deg', None),
        lead_arm_top_deg=getattr(m, 'lead_arm_top_deg', None),
        lead_arm_impact_deg=getattr(m, 'lead_arm_impact_deg', None),
        trail_elbow_address_deg=getattr(m, 'trail_elbow_address_deg', None),
        trail_elbow_top_deg=getattr(m, 'trail_elbow_top_deg', None),
        trail_elbow_impact_deg=getattr(m, 'trail_elbow_impact_deg', None),
        knee_flex_left_address_deg=getattr(m, 'knee_flex_left_address_deg', None),
        knee_flex_right_address_deg=getattr(m, 'knee_flex_right_address_deg', None),
        head_sway_range=getattr(m, 'head_sway_range', None),
        early_extension_amount=getattr(m, 'early_extension_amount', None),
        swing_path_index=getattr(m, 'swing_path_index', None),
        hand_height_at_top_index=getattr(m, 'hand_height_at_top_index', None),
        hand_width_at_top_index=getattr(m, 'hand_width_at_top_index', None),
        head_drop_cm=getattr(m, 'head_drop_cm', None),
        head_rise_cm=getattr(m, 'head_rise_cm', None),
        # Backward compatibility (old field names)
        shoulder_turn_top_deg=getattr(m, 'shoulder_turn_top_deg', None),
        hip_turn_top_deg=getattr(m, 'hip_turn_top_deg', None),
        spine_tilt_address_deg=getattr(m, 'spine_tilt_address_deg', None),
        spine_tilt_impact_deg=getattr(m, 'spine_tilt_impact_deg', None),
        head_movement_forward_cm=getattr(m, 'head_movement_forward_cm', None),
        head_movement_vertical_cm=getattr(m, 'head_movement_vertical_cm', None),
        shaft_lean_impact_deg=getattr(m, 'shaft_lean_impact_deg', None),
        lead_wrist_flexion_address_deg=getattr(m, 'lead_wrist_flexion_address_deg', None),
        lead_wrist_flexion_top_deg=getattr(m, 'lead_wrist_flexion_top_deg', None),
        lead_wrist_flexion_impact_deg=getattr(m, 'lead_wrist_flexion_impact_deg', None),
        lead_wrist_hinge_top_deg=getattr(m, 'lead_wrist_hinge_top_deg', None)
    )
    
    from reference.reference_profiles import get_reference_profile_for
    from reference.scoring import Scorer
    
    ref = get_reference_profile_for(s.club_type, s.view)
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref)
    
    feedback = _get_feedback_from_db(s.feedback)
    
    phases = SwingPhases(
        address_frame=s.phases.address_frame,
        top_frame=s.phases.top_frame,
        impact_frame=s.phases.impact_frame,
        finish_frame=s.phases.finish_frame
    )

    return AnalysisResponse(
        session_id=s.id,
        video_url=f"/api/v1/sessions/{s.id}/video" if s.video_url else None,
        is_personal_best=s.is_personal_best,
        metadata=SwingAnalysisRequest(
            handedness=s.handedness,
            view=s.view,
            club_type=s.club_type
        ),
        phases=phases,
        metrics=metrics,
        scores=scores,
        feedback=feedback
    )

@router.get("/sessions/{session_id}/video")
def get_session_video(
    session_id: str, 
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get video file for a session"""
    print(f"[DEBUG] get_session_video called for session {session_id}")
    
    # Manual Auth (since video tag doesn't send headers easily)
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.models.user import User
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            print("[DEBUG] Invalid token: no sub")
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as e:
        print(f"[DEBUG] JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
        
    current_user = db.query(User).filter(User.email == email).first()
    if not current_user or not current_user.is_active:
        print(f"[DEBUG] User not found or inactive: {email}")
        raise HTTPException(status_code=401, detail="Invalid user")

    # Check ownership
    repo = AnalysisRepository(db)
    print(f"[DEBUG] Querying session {session_id!r} (len={len(session_id)}) for user {current_user.id}")
    
    s = repo.get_session(session_id)
    if not s:
        print(f"[DEBUG] Session not found via repo.get_session")
        # List all sessions for this user to debug
        all_sessions = db.query(SwingSession).filter(SwingSession.user_id == current_user.id).all()
        print(f"[DEBUG] User has {len(all_sessions)} sessions:")
        for sess in all_sessions:
            print(f" - {sess.id} (match? {str(sess.id) == session_id})")
            
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        print(f"[DEBUG] Unauthorized access: user {current_user.id} vs session user {s.user_id}")
        raise HTTPException(status_code=403, detail="Not authorized")

    storage = VideoStorage()
    path = storage.get_video_path(session_id)
    print(f"[DEBUG] Video path for {session_id}: {path}")
    
    if not path:
        print(f"[DEBUG] Video file not found on disk for {session_id}")
        # Check if file exists manually to be sure
        expected_path = os.path.abspath(os.path.join("videos", f"{session_id}.mp4"))
        print(f"[DEBUG] Expected path: {expected_path}, Exists: {os.path.exists(expected_path)}")
        raise HTTPException(status_code=404, detail="Video not found")
        
    return FileResponse(path)

@router.get("/sessions/{session_id}/frames/{phase_name}")
def get_session_frame_image(
    session_id: str, 
    phase_name: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get key frame image (address, top, impact, finish)"""
    # ... (Auth logic omitted for brevity, keeping it concise or reusing imports)
    # Manual Auth (same as video)
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.models.user import User
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    current_user = db.query(User).filter(User.email == email).first()
    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")

    # Check ownership
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    key = f"videos/{session_id}_{phase_name}.jpg"
    storage = get_storage()
    image_path = None
    try:
        image_path = storage.get_path(key)
    except:
        pass
        
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Frame image not found")
        
    return FileResponse(image_path)


@router.get("/sessions/{session_id}/poses")
def get_session_poses(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Get pose data for a session"""
    # Check ownership
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Load original poses via storage
    key = f"videos/{session_id}_poses.json"
    storage = get_storage()
    try:
        poses_path = storage.get_path(key)
        if not os.path.exists(poses_path):
            return []
            
        import json
        with open(poses_path, "r") as f:
            poses_data = json.load(f)
        return poses_data
    except:
        return []

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Delete a session and all associated data"""
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Delete from DB
    repo.delete_session(session_id)
    
    # Delete files via storage
    storage = get_storage()
    
    # 1. Video
    # Try video_url field if it exists and looks like a key, else fallback
    if s.video_url:
        storage.delete(s.video_url)
    
    # 2. Poses
    storage.delete(f"videos/{session_id}_poses.json")
    
    # 3. Keyframes
    for phase in ["address", "top", "impact", "finish"]:
        storage.delete(f"videos/{session_id}_{phase}.jpg")
                
    return {"status": "success", "message": "Session deleted"}

@router.get("/sessions/{session_id}/key-frames")
def get_session_key_frames(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Get key frames (address, top, impact) with landmarks for skeleton visualization"""
    # Check ownership
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Load poses from JSON file via storage
    key = f"videos/{session_id}_poses.json"
    storage = get_storage()
    
    import json
    
    try:
        poses_path = storage.get_path(key)
        if not os.path.exists(poses_path):
            return []
        with open(poses_path, "r") as f:
            poses_data = json.load(f)
    except:
        return []
    
    # NOTE: Blending is now applied during analysis.
    
    # Convert to FramePose format
    from pose.types import FramePose, Point3D
    poses = []
    for i, p in enumerate(poses_data):
        landmarks = [
            Point3D(
                x=lm["x"],
                y=lm["y"],
                z=lm.get("z", 0.0),  # z might not be present in older data
                visibility=lm.get("visibility", 1.0)  # visibility might not be present
            )
            for lm in p.get("landmarks", [])
        ]
        # Handle both timestamp_ms and timestamp_sec formats
        timestamp_ms = p.get("timestamp_ms")
        if timestamp_ms is None and "timestamp_sec" in p:
            timestamp_ms = p["timestamp_sec"] * 1000.0
        
        pose = FramePose(
             frame_index=p.get("frame_index", 0),
             timestamp_ms=timestamp_ms or 0.0,
             landmarks=landmarks,
             smpl_pose=p.get("smpl_pose"),
             smpl_joints=p.get("smpl_joints") or p.get("smpl_joints_3d") or p.get("joints_3d_24") or p.get("joints_3d"),
             smpl_joints_2d=p.get("smpl_joints_2d") or p.get("joints_2d_29"),
             smpl_camera=p.get("smpl_camera"),
             smpl_bbox=p.get("smpl_bbox"),
        )
        poses.append(pose)
    
    # Extract key frames
    from pose.metrics import extract_key_frames
    phases = SwingPhases(
        address_frame=s.phases.address_frame,
        top_frame=s.phases.top_frame,
        impact_frame=s.phases.impact_frame,
        finish_frame=s.phases.finish_frame
    )
    
    key_frames = extract_key_frames(poses, phases)
    
    key_frames = extract_key_frames(poses, phases)
    
    # Load MHR data if available
    storage = get_storage()
    
    mhr_data = None
    mhr_key = f"videos/{session_id}_mhr.json"
    try:
        mhr_path = storage.get_path(mhr_key)
        if os.path.exists(mhr_path):
            with open(mhr_path, "r") as f:
                mhr_data = json.load(f)
            print(f"[KeyFrames] Loaded MHR data from {mhr_path}")
    except Exception as e:
        print(f"[KeyFrames] Failed to load MHR data: {e}")
    
    # Add image URLs
    pose_by_frame = {p.frame_index: p for p in poses}
    pose_data_by_frame = {p.get("frame_index"): p for p in poses_data}
    
    for kf in key_frames:
        phase_name = kf.get("phase")
        frame_idx = kf.get("frame_index")
        
        # Attach smpl_joints to key frame for frontend SMPL overlay
        if frame_idx is not None and frame_idx in pose_by_frame:
            kf["smpl_joints"] = getattr(pose_by_frame[frame_idx], "smpl_joints", None)
            kf["smpl_joints_2d"] = getattr(pose_by_frame[frame_idx], "smpl_joints_2d", None)
            kf["smpl_camera"] = getattr(pose_by_frame[frame_idx], "smpl_camera", None)
            kf["smpl_pose"] = getattr(pose_by_frame[frame_idx], "smpl_pose", None)
            kf["smpl_bbox"] = getattr(pose_by_frame[frame_idx], "smpl_bbox", None)
            
        # Also attach smpl_joints_2d_orig from raw data (FramePose drops it)
        if frame_idx is not None and frame_idx in pose_data_by_frame:
            kf["smpl_joints_2d_orig"] = pose_data_by_frame[frame_idx].get("smpl_joints_2d_orig")
        
        # Attach MHR joints2d for skeleton visualization (preferred over SMPL)
        if mhr_data and phase_name and phase_name in mhr_data:
            mhr_phase = mhr_data[phase_name]
            if mhr_phase.get("joints2d"):
                kf["mhr_joints_2d"] = mhr_phase["joints2d"]
            if mhr_phase.get("joints3d"):
                kf["mhr_joints_3d"] = mhr_phase["joints3d"]

        if phase_name:
            # Check if image exists using Storage
            image_key = f"videos/{session_id}_{phase_name}.jpg"
            try:
                image_path = storage.get_path(image_key)
                if os.path.exists(image_path):
                    kf["image_url"] = f"/api/v1/sessions/{session_id}/frames/{phase_name}"
            except:
                pass
                
    return key_frames

@router.post("/references", response_model=ReferenceProfileResponse)
def create_reference_profile(data: ReferenceProfileCreate, db: Session = Depends(get_db)):
    repo = AnalysisRepository(db)
    profile = repo.create_reference_profile(data)
    return ReferenceProfileResponse(
        id=profile.id,
        name=profile.name,
        is_default=bool(profile.is_default)
    )

@router.get("/references", response_model=List[ReferenceProfileResponse])
def list_reference_profiles(db: Session = Depends(get_db)):
    repo = AnalysisRepository(db)
    profiles = repo.list_reference_profiles()
    return [
        ReferenceProfileResponse(
            id=p.id,
            name=p.name,
            is_default=bool(p.is_default)
        ) for p in profiles
    ]


@router.post("/sessions/{session_id}/regenerate-feedback", response_model=SwingFeedback)
async def regenerate_feedback_endpoint(
    session_id: str,
    db: Session = Depends(get_db)
):
    analysis_repo = AnalysisRepository(db)
    session = analysis_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Generate new feedback
    feedback_service = FeedbackService()
    
    # We need to construct SwingMetrics and SwingScores from DB to pass to service
    if not session.metrics:
         raise HTTPException(status_code=400, detail="Metrics not found for session")

    metrics_data = {k: v for k, v in session.metrics.__dict__.items() if not k.startswith('_')}
    # Ensure all required fields for SwingMetrics are present (basic validation)
    # Pydantic will validate, but we might need to be careful with optional fields
    # Here we assume DB metrics row matches Pydantic schema sufficiently
    metrics = SwingMetrics(**metrics_data)
    
    # Re-calculate scores using current reference profile
    from reference.scoring import Scorer
    from reference.reference_profiles import get_reference_profile_for
    
    ref_profile = get_reference_profile_for(session.club_type, session.view)
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref_profile)
    
    with open("debug_log.txt", "a") as f:
        f.write(f"DEBUG: Regenerating feedback for {session_id}\n")
        f.write(f"DEBUG: Handedness: {session.handedness}, Club: {session.club_type}\n")

    # Generate
    feedback = feedback_service.generate_feedback(
        metrics=metrics, 
        scores=scores,
        handedness=session.handedness,
        club_type=session.club_type,
        db=db,
        reference_profile=ref_profile
    )
    
    with open("debug_log.txt", "a") as f:
        f.write(f"DEBUG: Generated feedback summary: {feedback.summary[:20]}...\n")
        f.write(f"DEBUG: Generated phase feedback keys: {feedback.phase_feedback.keys() if feedback.phase_feedback else 'None'}\n")

    # Save to DB - THIS IS KEY: save_feedback must handle phase_feedback
    analysis_repo.save_feedback(session.id, feedback)
    
    return feedback




@router.get("/sessions/{session_id}/report")
async def generate_report_endpoint(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a PDF report for the swing session.
    """
    analysis_repo = AnalysisRepository(db)
    session = analysis_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    report_service = ReportService()
    try:
        pdf_buffer = report_service.generate_report(session)
        
        headers = {
            'Content-Disposition': f'attachment; filename="SwingReport_{session_id[:8]}.pdf"'
        }
        
        return StreamingResponse(pdf_buffer, headers=headers, media_type='application/pdf')
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

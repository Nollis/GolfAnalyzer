from pathlib import Path
import os
import cv2
import json
import shutil
from sqlalchemy.orm import Session
from fastapi import HTTPException

# Models & Services
from app.models.db import SwingSession
from app.services.video_storage import VideoStorage
from app.services.feedback_service import FeedbackService
from app.services.analysis_repository import AnalysisRepository
from app.services.skill_assessment import SkillAssessmentService
from app.schemas import SwingAnalysisRequest, SwingPhases, SwingMetrics, SwingFeedback, DrillResponse

# Pose & Metrics
from pose.swing_detection import SwingDetector
from pose.metrics import MetricsCalculator
from pose.types import FramePose, Point3D
from pose.yolo_pose_extractor import extract_pose_frames_yolo, is_yolo_available
from reference.reference_profiles import get_reference_profile_for
from reference.scoring import Scorer

# MHR Pipeline
from pose.mhr_pipeline import analyze_with_mhr
from pose.mhr_sam3d_client import is_sam3d_available
from pose.mhr_metrics import compute_all_mhr_metrics
from pose.mhr_finish_metrics import compute_finish_metrics
from pose.mhr_sway_metrics import compute_all_sway_metrics
from pose.mhr_plane_metrics import compute_swing_plane_metrics

def run_analysis_pipeline(
    video_path: str,
    handedness: str,
    view: str,
    club_type: str,
    user_id: str,
    db: Session
):
    """
    Core analysis logic.
    Returns the saved SwingSession object (or just the ID).
    """
    tmp_path = video_path # Assume it's already a temp path or accessible file

    # 0. Video Props
    cap = cv2.VideoCapture(tmp_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if fps <= 0: fps = 30.0

    # 1. Pose Extraction (YOLO)
    poses = []
    hybrik_frames = None # Deprecated
    mhr_data = None
    
    if not is_yolo_available():
        raise Exception("YOLO unavailable")
        
    yolo_frames = extract_pose_frames_yolo(Path(tmp_path), frame_step=1)
    if not yolo_frames:
        raise Exception("YOLO extracted no frames")

    for yf in yolo_frames:
        landmarks = [
            Point3D(
                x=lm["x"],
                y=lm["y"],
                z=lm.get("z", 0.0),
                visibility=lm.get("visibility", 1.0),
            )
            for lm in yf["landmarks"]
        ]
        pose = FramePose(
            frame_index=yf["frame_index"],
            timestamp_ms=yf.get("timestamp_sec", 0) * 1000.0,
            landmarks=landmarks,
        )
        poses.append(pose)

    # 2. Swing Detection
    detector = SwingDetector()
    phases = detector.detect_swing_phases(poses, fps)

    # 2.5 MHR Analysis (SAM-3D)
    if is_sam3d_available():
        print("[MHR] Running SAM-3D MHR analysis...")
        try:
            mhr_data = analyze_with_mhr(Path(tmp_path), poses, fps, None)
        except Exception as e:
            print(f"[MHR] Failed: {e}")

    # 3. Metrics
    calculator = MetricsCalculator()
    metrics = calculator.compute_metrics(poses, phases, fps)

    # 3.5 Override with 3D MHR
    if mhr_data:
        # Check if basic phases are present in MHR data
        mhr_success = all(mhr_data.get(p, {}).get("joints3d") is not None 
                            for p in ["address", "top", "impact"])
        
        if mhr_success:
            try:
                mhr_metrics = compute_all_mhr_metrics(mhr_data, handedness=handedness or "Right")
                for key, value in mhr_metrics.items():
                    if value is not None and hasattr(metrics, key):
                        setattr(metrics, key, round(value, 2) if isinstance(value, float) else value)
            except Exception as e:
                print(f"[MHR] Metrics failed: {e}")

    # 3.6 Extended MHR Metrics
    extended_metrics = {}
    if mhr_data:
        try:
            # Finish metrics
            if mhr_data.get("finish", {}).get("joints3d") is not None:
                finish_metrics = compute_finish_metrics(mhr_data, handedness=handedness or "right")
                extended_metrics.update(finish_metrics)
            
            # Sway metrics
            sway_metrics = compute_all_sway_metrics(mhr_data)
            extended_metrics.update(sway_metrics)
            
            # Plane metrics
            plane_metrics = compute_swing_plane_metrics(mhr_data, handedness=handedness or "right")
            extended_metrics.update(plane_metrics)
            
        except Exception as e:
            print(f"[MHR] Extended metrics failed: {e}")
            
    # Auto-detect missing metadata
    if not handedness:
        handedness = calculator.detect_handedness(poses, phases)
    if not club_type:
        club_type = calculator.estimate_club_type(metrics)

    # 4. Scoring
    ref_profile = get_reference_profile_for(club_type, view)
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref_profile)

    # 5. Feedback
    feedback_service = FeedbackService()
    feedback = feedback_service.generate_feedback(metrics, scores, handedness, club_type, db, ref_profile)

    # 6. Skill Update (Side-effect)
    # Note: In worker, we need to fetch the User object properly if we want to update skill.
    # For now, we skip skill update if user object isn't passed or fetch it from DB.
    # user = db.query(User).get(user_id) ...

    # 7. Persistence
    repo = AnalysisRepository(db)
    
    # Check PB
    max_score_session = db.query(SwingSession).filter(
        SwingSession.user_id == user_id,
        SwingSession.club_type == club_type,
        SwingSession.view == view
    ).order_by(SwingSession.overall_score.desc()).first()
    
    is_pb = False
    if not max_score_session or scores.overall_score > max_score_session.overall_score:
        is_pb = True
        if max_score_session and max_score_session.is_personal_best:
            max_score_session.is_personal_best = False
            db.add(max_score_session)

    db_session = repo.save_analysis(
        metadata=SwingAnalysisRequest(handedness=handedness, view=view, club_type=club_type),
        metrics=metrics,
        phases=phases,
        scores=scores,
        feedback=feedback,
        video_path=None,
        user_id=user_id
    )

    if is_pb:
        db_session.is_personal_best = True
        db.add(db_session)
        db.commit()

    # Save Video
    video_storage = VideoStorage()
    saved_video_path = video_storage.save_video(tmp_path, db_session.id)
    
    # Extract Keyframes (Images)
    _extract_keyframes(saved_video_path, phases, db_session.id)

    # Save JSON Artifacts (Poses)
    _save_poses_json(db_session.id, poses, mhr_data, extended_metrics)
    
    # Update Session with final video path
    db_session.video_url = saved_video_path
    db.commit()

    return {
        "session_id": db_session.id,
        "score": scores.overall_score
    }

def _extract_keyframes(video_key_or_path, phases, session_id):
    try:
        from app.core.storage import get_storage
        storage = get_storage()
        
        # Resolve real path via storage (needed for cv2)
        # If video_key_or_path is a key, get path. If it's a path, use it.
        try:
             video_path = storage.get_path(video_key_or_path)
        except:
             video_path = video_key_or_path
             
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            indices = {
                "address": phases.address_frame,
                "top": phases.top_frame,
                "impact": phases.impact_frame,
                "finish": phases.finish_frame,
            }
            
            import tempfile
            for name, idx in indices.items():
                if idx is not None and idx >= 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret:
                        # Write to temp -> Storage
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                            tmp_name = tmp.name
                        
                        cv2.imwrite(tmp_name, frame)
                        
                        # Save to storage: videos/{session_id}_{name}.jpg (keeping flat structure to match current frontend expectations via routes)
                        # Ideal: thumbnails/{session_id}/{name}.jpg
                        # But routes_analyze.py expects videos/{session_id}_{name}.jpg key pattern if we use local storage mapping?
                        # Actually, let's stick to the key convention that matches the current serving logic or update serving logic.
                        # Current serving logic: reads from "videos/" dir.
                        # New serving logic: storage.get_path(key).
                        # Let's use key: "videos/{session_id}_{name}.jpg" to minimize frontend URL breakage if we map keys.
                        
                        key = f"videos/{session_id}_{name}.jpg"
                        storage.save(tmp_name, key)
                        os.remove(tmp_name)

        cap.release()
    except Exception as e:
        print(f"Keyframe extraction failed: {e}")

def _save_poses_json(session_id, poses, mhr_data, extended_metrics):
    from app.core.storage import get_storage
    storage = get_storage()
    import tempfile

    # Determine pose dicts
    poses_data = []
    for p in poses:
        poses_data.append({
            "frame_index": p.frame_index,
            "timestamp_ms": p.timestamp_ms,
            "landmarks": [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in p.landmarks]
        })
    
    # Save Poses
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(poses_data, tmp)
        tmp_poses = tmp.name
        
    storage.save(tmp_poses, f"videos/{session_id}_poses.json")
    os.remove(tmp_poses)
        
    if mhr_data:
        # Save MHR
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
             json.dump({"extended_metrics": extended_metrics}, tmp, default=str)
             tmp_mhr = tmp.name
             
        storage.save(tmp_mhr, f"videos/{session_id}_mhr.json")
        os.remove(tmp_mhr)

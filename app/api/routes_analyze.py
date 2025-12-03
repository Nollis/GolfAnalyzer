from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Query
from app.schemas import AnalysisResponse, SwingPhases, SwingMetrics, SwingScores, SwingFeedback, SwingAnalysisRequest, MetricScore, Drill, ReferenceProfileCreate, ReferenceProfileResponse
from pose.mediapipe_wrapper import MediaPipeWrapper
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
import cv2
from sqlalchemy.orm import Session
from app.core.database import get_db, Base, engine
from fastapi import Depends
from app.services.analysis_repository import AnalysisRepository
from app.services.video_storage import VideoStorage
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.db import SwingSession
from typing import List, Optional
from fastapi.responses import FileResponse

# Create tables on startup (for dev simplicity)
Base.metadata.create_all(bind=engine)


def _get_feedback_from_db(feedback_db) -> SwingFeedback:
    """Convert database feedback to SwingFeedback schema, handling None."""
    if feedback_db:
        return SwingFeedback(
            summary=feedback_db.summary,
            priority_issues=feedback_db.priority_issues if feedback_db.priority_issues else [],
            drills=[Drill(**d) for d in (feedback_db.drills if feedback_db.drills else [])]
        )
    else:
        return SwingFeedback(
            summary="Feedback generation was disabled for this analysis.",
            priority_issues=[],
            drills=[]
        )


router = APIRouter()

@router.post("/analyze-swing", response_model=AnalysisResponse, 
              summary="Analyze swing (synchronous)",
              description="""
Synchronous analysis endpoint. Waits for full analysis to complete before returning.

**For better performance, use the async endpoint instead:**
- POST /api/v1/jobs/analyze - Returns immediately with job_id
- GET /api/v1/jobs/{job_id} - Poll for status/progress
- When status is 'completed', session_id contains the results

The async pattern is recommended for:
- Production deployments
- Large videos
- Multiple concurrent users
""")
async def analyze_swing(
    video: UploadFile = File(...),
    handedness: Optional[str] = Form(None),
    view: str = Form(...),
    club_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Save uploaded file to temp
    suffix = ".mp4" # Assume mp4 or grab from filename
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        # Get FPS
        cap = cv2.VideoCapture(tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if fps <= 0: fps = 30.0
        
        # 1. Pose Extraction - Try HybrIK first, fallback to MediaPipe
        hybrik_frames = None
        poses = None
        pose_method = "unknown"
        
        if HYBRIK_AVAILABLE and is_smpl_available():
            try:
                print("Attempting HybrIK 3D pose extraction...")
                extractor = get_hybrik_extractor()
                if extractor:
                    if not extractor._loaded:
                        print("Loading HybrIK model (first time may take 30-60s)...")
                        extractor.load_model()

                    print("Extracting poses from video with HybrIK...")
                    hybrik_frames = extractor.extract_video(Path(tmp_path), frame_step=2)

                    if hybrik_frames:
                        from pose.mediapipe_wrapper import FramePose, Point3D
                        poses = []
                        for smpl_frame in hybrik_frames:
                            mp_frame = smpl_to_mediapipe_format(smpl_frame)
                            landmarks = [
                                Point3D(
                                    x=lm["x"],
                                    y=lm["y"],
                                    z=lm["z"],
                                    visibility=lm["visibility"],
                                )
                                for lm in mp_frame["landmarks"]
                            ]
                            pose = FramePose(
                                frame_index=mp_frame.get("frame_idx", 0),
                                timestamp_ms=mp_frame.get("timestamp", 0) * 1000.0,
                                landmarks=landmarks,
                            )
                            poses.append(pose)

                        pose_method = "HybrIK 3D"
                        print(f"HybrIK extracted {len(poses)} frames with 3D SMPL data")
                    else:
                        print("HybrIK returned no frames")
                else:
                    print("Could not get HybrIK extractor")
            except Exception as e:
                print(f"HybrIK extraction failed: {e}, falling back to MediaPipe")
                import traceback
                traceback.print_exc()
                hybrik_frames = None
        
        # Fallback to MediaPipe if HybrIK not available or failed
        if poses is None or len(poses) == 0:
            print("Using MediaPipe 2D pose estimation (fallback)")
            mp_wrapper = MediaPipeWrapper()
            poses = mp_wrapper.extract_poses_from_video(tmp_path)
            pose_method = "MediaPipe 2D"
            print(f"MediaPipe extracted {len(poses)} frames")
            print("Note: 2D estimation has limited accuracy for rotation metrics in DTL videos")

        # 1.5. Address Pose Blending & FK Update (if DTL)
        # We need to do this BEFORE metrics calculation so metrics reflect the blended pose
        if view in ["dtl", "down_the_line"] and hybrik_frames:
            print("[INFO] Applying address pose blending and updating metrics...")
            from pose.presets.address_blend import blend_with_address
            from pose.kinematics import forward_kinematics, estimate_skeleton_offsets
            
            for i, frame in enumerate(hybrik_frames):
                smpl_pose = frame.get("smpl_pose") # (24, 3, 3)
                joints_3d = frame.get("joints_3d_24") # (24, 3)
                
                if smpl_pose is not None and joints_3d is not None:
                    # 1. Blend rotations
                    blended_pose = blend_with_address(smpl_pose)
                    frame["smpl_pose"] = blended_pose
                    
                    # 2. Estimate bone offsets from original joints (to preserve scale)
                    offsets = estimate_skeleton_offsets(joints_3d)
                    
                    # 3. Re-compute joints using FK
                    # Use original root position
                    root_pos = joints_3d[0]
                    new_joints = forward_kinematics(blended_pose, root_pos, offsets)
                    
                    # 4. Update frame data
                    frame["joints_3d_24"] = np.array(new_joints)
                    # Also update generic joints_3d if present
                    if "joints_3d" in frame:
                        frame["joints_3d"] = np.array(new_joints)

        # 2. Swing Detection - Pass HybrIK frames if available
        detector = SwingDetector()
        phases = detector.detect_swing_phases(poses, fps, hybrik_frames=hybrik_frames)

        # 3. Metrics - Pass HybrIK frames if available
        calculator = MetricsCalculator()
        metrics = calculator.compute_metrics(poses, phases, fps, hybrik_frames=hybrik_frames)

        # Auto-detect if missing
        if not handedness:
            handedness = calculator.detect_handedness(poses, phases)
            print(f"Auto-detected handedness: {handedness}")
            
        if not club_type:
            club_type = calculator.estimate_club_type(metrics)
            print(f"Auto-detected club type: {club_type}")

        # 4. Scoring - Always use default pro profile
        ref_profile = get_reference_profile_for(club_type, view)
            
        scorer = Scorer()
        scores = scorer.build_scores(metrics, ref_profile)

        # 5. Feedback
        feedback_service = FeedbackService()
        feedback = feedback_service.generate_feedback(metrics, scores, handedness, club_type, ref_profile)

        # 5.1 Skill Assessment
        from app.services.skill_assessment import SkillAssessmentService
        skill_service = SkillAssessmentService()
        new_skill = skill_service.update_user_skill(current_user, metrics, scores)
        print(f"User skill assessed as: {new_skill}")

        # 6. Persistence
        repo = AnalysisRepository(db)
        
        # Automatic Personal Best Detection
        # Check if this score is higher than any existing session for this user/club/view
        from app.models.db import SwingSession
        max_score_session = db.query(SwingSession).filter(
            SwingSession.user_id == current_user.id,
            SwingSession.club_type == club_type,
            SwingSession.view == view
        ).order_by(SwingSession.overall_score.desc()).first()
        
        is_pb = False
        if not max_score_session or scores.overall_score > max_score_session.overall_score:
            is_pb = True
            print(f"New Personal Best! Score: {scores.overall_score}")
            # Optional: Unset previous PB if we want strict single PB
            if max_score_session and max_score_session.is_personal_best:
                max_score_session.is_personal_best = False
                db.add(max_score_session)
        
        # First save the session to get an ID
        db_session = repo.save_analysis(
            metadata=SwingAnalysisRequest(handedness=handedness, view=view, club_type=club_type),
            metrics=metrics,
            phases=phases,
            scores=scores,
            feedback=feedback,
            video_path=None,
            user_id=current_user.id
        )
        
        if is_pb:
            db_session.is_personal_best = True
            db.add(db_session)
            db.commit()
        
        # Now save the video permanently using the session ID
        video_storage = VideoStorage()
        saved_video_path = video_storage.save_video(tmp_path, db_session.id)
        
        # Extract and save key frame images (address/top/impact/finish)
        try:
            from pathlib import Path as _Path
            abs_video_path = os.path.abspath(saved_video_path)
            print(f"📸 Extracting key frame images from {abs_video_path}...")
            
            cap = cv2.VideoCapture(abs_video_path)
            
            # Fallback to original tmp video if saved one fails
            if not cap.isOpened():
                print(f"⚠️ Failed to open saved video: {abs_video_path}, falling back to original")
                cap = cv2.VideoCapture(tmp_path)
            
            if cap.isOpened():
                key_frame_indices = {
                    "address": phases.address_frame,
                    "top": phases.top_frame,
                    "impact": phases.impact_frame,
                    "finish": phases.finish_frame,
                }
                for phase_name, frame_idx in key_frame_indices.items():
                    if frame_idx is not None and frame_idx >= 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                        ret, frame = cap.read()
                        if ret:
                            image_filename = f"{db_session.id}_{phase_name}.jpg"
                            image_path = _Path("videos") / image_filename
                            cv2.imwrite(str(image_path), frame)
                            print(f"✅ Saved {phase_name} image to {image_path}")
                        else:
                            print(f"⚠️ Could not read frame {frame_idx} for {phase_name}")
                cap.release()
            else:
                print("⚠️ Failed to open video file (both saved and original failed)")
        except Exception as e:
            print(f"⚠️ Failed to extract key frame images: {e}")
        
        # Save poses to JSON
        import json
        poses_data = []
        def to_list_safe(x):
            if x is None:
                return None
            try:
                import numpy as np
                if isinstance(x, np.ndarray):
                    return x.tolist()
            except Exception:
                pass
            if isinstance(x, list):
                return x
            try:
                return x.tolist()
            except Exception:
                return x

        if hybrik_frames:
            # Prefer HybrIK outputs: include SMPL pose + joints; derive landmarks from SMPL joints
            for f in hybrik_frames:
                joints = f.get("joints_3d_24")
                if joints is None:
                    joints = f.get("joints_3d")
                joints_list = to_list_safe(joints)
                joints2d_list = to_list_safe(f.get("joints_2d_29"))
                cam = to_list_safe(f.get("pred_camera"))
                bbox = to_list_safe(f.get("bbox"))
                # Lift 2D joints back into original image pixel coords if bbox is available
                joints2d_orig = None
                if bbox and joints2d_list and len(bbox) >= 4:
                    try:
                        x1, y1, x2, y2 = bbox
                        joints2d_orig = [
                            [x1 + pt[0], y1 + pt[1]] if pt and len(pt) >= 2 else None
                            for pt in joints2d_list
                        ]
                    except Exception:
                        joints2d_orig = None
                mp_frame = smpl_to_mediapipe_format(f)  # includes 2D landmarks from HybrIK if available
                poses_data.append({
                    "frame_index": f.get("frame_idx", 0),
                    "timestamp_ms": f.get("timestamp", 0) * 1000.0,
                    "landmarks": mp_frame.get("landmarks", []),
                    "smpl_landmarks": mp_frame.get("landmarks", []),
                    "smpl_pose": to_list_safe(f.get("smpl_pose")),
                    "smpl_joints": joints_list,
                    "smpl_joints_2d": joints2d_list,
                    "smpl_joints_2d_orig": joints2d_orig,
                    "smpl_camera": cam,
                    "smpl_bbox": bbox,
                })
        else:
            for p in poses:
                poses_data.append({
                    "frame_index": p.frame_index,
                    "timestamp_ms": p.timestamp_ms,
                    "landmarks": [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in p.landmarks],
                    "smpl_pose": to_list_safe(getattr(p, "smpl_pose", None)),
                    "smpl_joints": to_list_safe(getattr(p, "smpl_joints_3d", None) or getattr(p, "joints_3d_24", None)),
                })
            
        poses_path = os.path.join("videos", f"{db_session.id}_poses.json")
        with open(poses_path, "w") as f:
            json.dump(poses_data, f)
        
        # Update session with video path
        db_session.video_url = saved_video_path
        db.commit()

        return AnalysisResponse(
            session_id=db_session.id,
            video_url=f"/api/v1/sessions/{db_session.id}/video",
            is_personal_best=db_session.is_personal_best,
            metadata=SwingAnalysisRequest(
                handedness=handedness,
                view=view,
                club_type=club_type
            ),
            phases=phases,
            metrics=metrics,
            scores=scores,
            feedback=feedback
        )

    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/sessions", response_model=List[AnalysisResponse])
def list_sessions(limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # Filter by user
    sessions = db.query(SwingSession).filter(SwingSession.user_id == current_user.id).order_by(SwingSession.created_at.desc()).limit(limit).all()
    
    results = []
    for s in sessions:
        # Helper to map metrics
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
        
        # Feedback
        feedback = _get_feedback_from_db(s.feedback)
        
        phases = SwingPhases(
            address_frame=s.phases.address_frame,
            top_frame=s.phases.top_frame,
            impact_frame=s.phases.impact_frame,
            finish_frame=s.phases.finish_frame
        )

        results.append(AnalysisResponse(
            session_id=s.id,
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

@router.post("/sessions/{session_id}/regenerate-feedback", response_model=SwingFeedback)
def regenerate_feedback(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Regenerate AI feedback for an existing session.
    Useful if you want updated feedback or if feedback generation failed initially.
    """
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Reconstruct metrics and scores
    m = s.metrics
    metrics = SwingMetrics(
        tempo_ratio=m.tempo_ratio,
        backswing_duration_ms=m.backswing_duration_ms,
        downswing_duration_ms=m.downswing_duration_ms,
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
    
    ref_profile = get_reference_profile_for(s.club_type, s.view)
    scorer = Scorer()
    scores = scorer.build_scores(metrics, ref_profile)
    
    # Generate new feedback
    feedback_service = FeedbackService()
    feedback = feedback_service.generate_feedback(metrics, scores, s.handedness, s.club_type, ref_profile)
    
    # Update or create feedback in database
    from app.models.db import SwingFeedbackDB
    if s.feedback:
        f = s.feedback
        f.summary = feedback.summary
        f.priority_issues = feedback.priority_issues
        f.drills = [d.dict() if hasattr(d, 'dict') else d.model_dump() for d in feedback.drills]
    else:
        f = SwingFeedbackDB(
            session_id=s.id,
            summary=feedback.summary,
            priority_issues=feedback.priority_issues,
            drills=[d.dict() if hasattr(d, 'dict') else d.model_dump() for d in feedback.drills]
        )
    db.add(f)
    db.commit()
    
    return feedback

@router.get("/sessions/{session_id}/video")
def get_session_video(
    session_id: str, 
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Stream video with token authentication"""
    # Manual Auth for video streaming (since <video> tag can't send headers)
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

    storage = VideoStorage()
    path = storage.get_video_path(session_id)
    if not path:
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

    image_filename = f"{session_id}_{phase_name}.jpg"
    image_path = os.path.join("videos", image_filename)
    
    if not os.path.exists(image_path):
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

    # Check for corrected poses first
    corrected_path = os.path.join("videos", f"{session_id}_poses_corrected.json")
    poses_path = corrected_path if os.path.exists(corrected_path) else os.path.join("videos", f"{session_id}_poses.json")

    if not os.path.exists(poses_path):
        return []
        
    import json
    with open(poses_path, "r") as f:
        poses_data = json.load(f)
        
    # NOTE: Blending is now applied during analysis (analyze_swing), so we don't need to apply it here.
    # If we apply it again, it might double-blend (though slerp with same target is idempotent-ish, it's wasteful).
    # However, for OLD sessions that weren't blended during analysis, we might still want it.
    # But since we overwrote the file, we can't easily distinguish.
    # Actually, analyze_swing saves to the DB and JSON.
    # If we want to support old sessions, we'd need a flag.
    # For now, let's assume new uploads get the fix.
    # If the user wants to fix old sessions, they can re-upload.
    # OR: We can check if "blended" flag is in metadata? No.
    
    # Let's keep it simple: Remove dynamic blending here since it's baked in now.
    # If we really need it for old sessions, we can add a check later.
                
    return poses_data

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
    
    # Load poses from JSON file
    # Check for corrected poses first
    poses_path = os.path.join("videos", f"{session_id}_poses_corrected.json")
    if not os.path.exists(poses_path):
        poses_path = os.path.join("videos", f"{session_id}_poses.json")
        
    if not os.path.exists(poses_path):
        return []
    
    import json
    with open(poses_path, "r") as f:
        poses_data = json.load(f)
        
    # NOTE: Blending is now applied during analysis.
    
    # Convert to FramePose format
    from pose.mediapipe_wrapper import FramePose, Point3D
    # Convert to FramePose format
    from pose.mediapipe_wrapper import FramePose, Point3D
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

        if phase_name:
            # Check if image exists
            image_filename = f"{session_id}_{phase_name}.jpg"
            image_path = os.path.join("videos", image_filename)
            if os.path.exists(image_path):
                kf["image_url"] = f"/api/v1/sessions/{session_id}/frames/{phase_name}"
                
    return key_frames

@router.post("/sessions/{session_id}/pose-corrections")
def save_pose_corrections(
    session_id: str, 
    corrections: dict = Body(...),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Save manual pose corrections and recalculate metrics.
    
    corrections format: { corrections: { frameIndex: { jointIndex: {x, y, z} } } }
    """
    import json
    import math
    
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Save corrections to a JSON file
    corrections_path = os.path.join("videos", f"{session_id}_corrections.json")
    with open(corrections_path, "w") as f:
        json.dump(corrections, f, indent=2)
    
    # Load original poses
    poses_path = os.path.join("videos", f"{session_id}_poses.json")
    if not os.path.exists(poses_path):
        return {"status": "partial", "message": "Corrections saved but no poses to recalculate"}
    
    with open(poses_path, "r") as f:
        poses_data = json.load(f)
    
    # Apply corrections to poses
    correction_data = corrections.get("corrections", {})
    corrected_poses = apply_pose_corrections(poses_data, correction_data)
    
    # Save corrected poses
    corrected_path = os.path.join("videos", f"{session_id}_poses_corrected.json")
    with open(corrected_path, "w") as f:
        json.dump(corrected_poses, f)
    
    # Convert to FramePose format for metrics calculation
    from pose.mediapipe_wrapper import FramePose, Point3D
    poses = []
    for p in corrected_poses:
        landmarks = [
            Point3D(
                x=lm["x"],
                y=lm["y"],
                z=lm.get("z", 0.0),
                visibility=lm.get("visibility", 1.0)
            )
            for lm in p.get("landmarks", [])
        ]
        pose = FramePose(
            frame_index=p.get("frame_index", 0),
            timestamp_ms=p.get("timestamp_ms", 0.0),
            landmarks=landmarks
        )
        poses.append(pose)
    
    if not poses:
        return {"status": "partial", "message": "Corrections saved but could not parse poses"}
    
    # Get phases from session
    phases = SwingPhases(
        address_frame=s.phases.address_frame,
        top_frame=s.phases.top_frame,
        impact_frame=s.phases.impact_frame,
        finish_frame=s.phases.finish_frame
    )
    
    # Recalculate metrics
    calculator = MetricsCalculator()
    fps = 30.0  # Default FPS
    new_metrics = calculator.compute_metrics(poses, phases, fps)
    
    # Recalculate scores
    ref_profile = get_reference_profile_for(s.club_type, s.view)
    scorer = Scorer()
    new_scores = scorer.build_scores(new_metrics, ref_profile)
    
    # Update database with new metrics
    m = s.metrics
    if m:
        # Update all metric fields
        m.tempo_ratio = new_metrics.tempo_ratio
        m.backswing_duration_ms = new_metrics.backswing_duration_ms
        m.downswing_duration_ms = new_metrics.downswing_duration_ms
        m.chest_turn_top_deg = new_metrics.chest_turn_top_deg
        m.pelvis_turn_top_deg = new_metrics.pelvis_turn_top_deg
        m.x_factor_top_deg = new_metrics.x_factor_top_deg
        m.spine_angle_address_deg = new_metrics.spine_angle_address_deg
        m.spine_angle_impact_deg = new_metrics.spine_angle_impact_deg
        m.lead_arm_address_deg = new_metrics.lead_arm_address_deg
        m.lead_arm_top_deg = new_metrics.lead_arm_top_deg
        m.lead_arm_impact_deg = new_metrics.lead_arm_impact_deg
        m.trail_elbow_address_deg = new_metrics.trail_elbow_address_deg
        m.trail_elbow_top_deg = new_metrics.trail_elbow_top_deg
        m.trail_elbow_impact_deg = new_metrics.trail_elbow_impact_deg
        m.knee_flex_left_address_deg = new_metrics.knee_flex_left_address_deg
        m.knee_flex_right_address_deg = new_metrics.knee_flex_right_address_deg
        m.head_sway_range = new_metrics.head_sway_range
        m.early_extension_amount = new_metrics.early_extension_amount
        db.add(m)
    
    # Update overall score
    s.overall_score = new_scores.overall_score
    db.add(s)
    db.commit()
    
    return {
        "status": "success", 
        "message": "Corrections applied and metrics recalculated",
        "corrections_count": sum(len(joints) for joints in correction_data.values()),
        "new_overall_score": new_scores.overall_score
    }


def apply_pose_corrections(poses_data: list, corrections: dict) -> list:
    """
    Apply rotation corrections to pose landmarks and SMPL matrices.
    """
    import math
    import numpy as np
    from scipy.spatial.transform import Rotation as R
    
    corrected = []
    
    # Mapping from SMPL joint indices to MediaPipe pivot landmarks
    SMPL_TO_MP_PIVOT = {
        16: 11, # L Shoulder
        17: 12, # R Shoulder
        18: 13, # L Elbow
        19: 14, # R Elbow
        1: 23,  # L Hip
        2: 24,  # R Hip
        4: 25,  # L Knee
        5: 26,  # R Knee
    }

    # Subtrees to rotate for each pivot (MediaPipe indices)
    MP_SUBTREES = {
        11: [13, 15, 17, 19, 21], # L Shoulder -> Arm
        12: [14, 16, 18, 20, 22], # R Shoulder -> Arm
        13: [15, 17, 19, 21],     # L Elbow -> Forearm
        14: [16, 18, 20, 22],     # R Elbow -> Forearm
        23: [25, 27, 29, 31],     # L Hip -> Leg
        24: [26, 28, 30, 32],     # R Hip -> Leg
        25: [27, 29, 31],         # L Knee -> Lower Leg
        26: [28, 30, 32],         # R Knee -> Lower Leg
    }
    
    for pose in poses_data:
        frame_idx = str(pose.get("frame_index", 0))
        
        if frame_idx not in corrections:
            corrected.append(pose)
            continue
        
        # Deep copy the pose
        new_pose = {
            "frame_index": pose.get("frame_index"),
            "timestamp_ms": pose.get("timestamp_ms"),
            "landmarks": [lm.copy() for lm in pose.get("landmarks", [])]
        }
        
        frame_corrections = corrections[frame_idx]
        landmarks = new_pose["landmarks"]
        
        # 1. Apply corrections to Landmarks (Hierarchical)
        for joint_idx_str, rot in frame_corrections.items():
            smpl_idx = int(joint_idx_str)
            
            if smpl_idx in SMPL_TO_MP_PIVOT:
                pivot_idx = SMPL_TO_MP_PIVOT[smpl_idx]
                
                if pivot_idx < len(landmarks):
                    pivot = landmarks[pivot_idx]
                    subtree_indices = MP_SUBTREES.get(pivot_idx, [])
                    
                    # Create rotation matrix
                    rx = math.radians(rot.get("x", 0))
                    ry = math.radians(rot.get("y", 0))
                    rz = math.radians(rot.get("z", 0))
                    
                    # Euler to Matrix (XYZ order matches frontend)
                    # Using scipy for consistent rotation
                    r = R.from_euler('xyz', [rx, ry, rz], degrees=False)
                    rot_mat = r.as_matrix()
                    
                    pivot_vec = np.array([pivot["x"], pivot["y"], pivot.get("z", 0)])
                    
                    for child_idx in subtree_indices:
                        if child_idx < len(landmarks):
                            child = landmarks[child_idx]
                            child_vec = np.array([child["x"], child["y"], child.get("z", 0)])
                            
                            # Rotate relative to pivot
                            rel_vec = child_vec - pivot_vec
                            rotated_vec = rot_mat @ rel_vec
                            new_vec = pivot_vec + rotated_vec
                            
                            child["x"] = float(new_vec[0])
                            child["y"] = float(new_vec[1])
                            child["z"] = float(new_vec[2])

        # 2. Apply corrections to SMPL Pose (Matrices)
        if "smpl_pose" in pose:
            try:
                # smpl_pose is a list of 24 3x3 matrices
                smpl_pose = np.array(pose["smpl_pose"])
                
                for joint_idx_str, rot in frame_corrections.items():
                    joint_idx = int(joint_idx_str)
                    if joint_idx < len(smpl_pose):
                        # Get current rotation matrix
                        current_mat = smpl_pose[joint_idx]
                        
                        # Create correction rotation
                        rx = rot.get("x", 0)
                        ry = rot.get("y", 0)
                        rz = rot.get("z", 0)
                        
                        correction_rot = R.from_euler('xyz', [rx, ry, rz], degrees=True)
                        correction_mat = correction_rot.as_matrix()
                        
                        # Apply correction: R_new = R_old @ R_correction
                        new_mat = current_mat @ correction_mat
                        smpl_pose[joint_idx] = new_mat
                
                new_pose["smpl_pose"] = smpl_pose.tolist()
                print(f"Applied SMPL corrections for frame {frame_idx}: {frame_corrections}")
            except Exception as e:
                print(f"Error applying SMPL corrections: {e}")
                import traceback
                traceback.print_exc()
                new_pose["smpl_pose"] = pose["smpl_pose"]
        
        corrected.append(new_pose)
    
    return corrected


@router.get("/sessions/{session_id}/pose-corrections")
def get_pose_corrections(
    session_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Get saved pose corrections for a session."""
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import json
    
    corrections_path = os.path.join("videos", f"{session_id}_corrections.json")
    if os.path.exists(corrections_path):
        with open(corrections_path, "r") as f:
            return json.load(f)
    
    return {"corrections": {}}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Delete a session and its associated files"""
    repo = AnalysisRepository(db)
    s = repo.get_session(session_id)
    
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check ownership
    if s.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this session")
    
    # Delete video file if exists
    if s.video_url:
        storage = VideoStorage()
        video_path = storage.get_video_path(session_id)
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
    
    # Delete pose data if exists
    poses_path = os.path.join("videos", f"{session_id}_poses.json")
    if os.path.exists(poses_path):
        os.remove(poses_path)
    
    # Delete from database (cascade will handle related records)
    db.delete(s)
    db.commit()
    
    return {"status": "success", "message": "Session deleted"}

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




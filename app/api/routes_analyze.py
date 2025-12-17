from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Query
from app.schemas import AnalysisResponse, SwingPhases, SwingMetrics, SwingScores, SwingFeedback, SwingAnalysisRequest, MetricScore, DrillResponse, ReferenceProfileCreate, ReferenceProfileResponse
from pose.legacy_mediapipe import MediaPipeWrapper
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
        
        # 1. Pose Extraction - Try YOLO first (fast), then HybrIK (3D), fallback to MediaPipe
        hybrik_frames = None
        poses = None
        pose_method = "unknown"
        
        # Try YOLO first (fastest and most consistent for phase detection)
        try:
            from pose.yolo_pose_extractor import extract_pose_frames_yolo, is_yolo_available
            if is_yolo_available():
                print("🎯 Using YOLOv8 for fast pose extraction...")
                yolo_frames = extract_pose_frames_yolo(Path(tmp_path), frame_step=1)
                
                if yolo_frames and len(yolo_frames) > 0:
                    from pose.types import FramePose, Point3D
                    poses = []
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
                    
                    pose_method = "YOLOv8"
                    print(f"✅ YOLO extracted {len(poses)} frames")
        except Exception as e:
            print(f"⚠️ YOLO extraction failed: {e}, trying HybrIK...")
            import traceback
            traceback.print_exc()
        
        # NOTE: HybrIK is disabled - being replaced by SAM-3D MHR for 3D poses
        # The GPU is needed for SAM-3D, so HybrIK is commented out to avoid conflicts
        # YOLO is used for fast 2D phase detection, SAM-3D for detailed 3D joints
        
        # if HYBRIK_AVAILABLE and is_smpl_available():
        #     try:
        #         print("Attempting HybrIK 3D pose extraction...")
        #         extractor = get_hybrik_extractor()
        #         if extractor:
        #             if not extractor._loaded:
        #                 print("Loading HybrIK model (first time may take 30-60s)...")
        #                 extractor.load_model()
        #
        #             print("Extracting poses from video with HybrIK...")
        #             hybrik_frames = extractor.extract_video(Path(tmp_path), frame_step=1)
        #
        #             # If YOLO didn't work, use HybrIK poses
        #             if hybrik_frames and (poses is None or len(poses) == 0):
        #                 from pose.types import FramePose, Point3D
        #                 poses = []
        #                 for smpl_frame in hybrik_frames:
        #                     mp_frame = smpl_to_mediapipe_format(smpl_frame)
        #                     landmarks = [
        #                         Point3D(
        #                             x=lm["x"],
        #                             y=lm["y"],
        #                             z=lm["z"],
        #                             visibility=lm["visibility"],
        #                         )
        #                         for lm in mp_frame["landmarks"]
        #                     ]
        #                     pose = FramePose(
        #                         frame_index=mp_frame.get("frame_idx", 0),
        #                         timestamp_ms=mp_frame.get("timestamp", 0) * 1000.0,
        #                         landmarks=landmarks,
        #                     )
        #                     poses.append(pose)
        #
        #                 pose_method = "HybrIK 3D"
        #                 print(f"HybrIK extracted {len(poses)} frames with 3D SMPL data")
        #             elif hybrik_frames:
        #                 print(f"HybrIK extracted {len(hybrik_frames)} 3D frames (YOLO used for phases)")
        #         else:
        #             print("Could not get HybrIK extractor")
        #     except Exception as e:
        #         print(f"HybrIK extraction failed: {e}, falling back to MediaPipe")
        #         import traceback
        #         traceback.print_exc()
        #         hybrik_frames = None
        
        # Fallback to MediaPipe if YOLO failed
        if poses is None or len(poses) == 0:
            print("Using MediaPipe 2D pose estimation (fallback)")
            mp_wrapper = MediaPipeWrapper()
            poses = mp_wrapper.extract_poses_from_video(tmp_path)
            pose_method = "MediaPipe 2D"
            
        # 1.5. Temporal Smoothing - DISABLED (HybrIK disabled)
        # Will be replaced with MHR-based smoothing later
        # if hybrik_frames:
        #     ... (temporal smoothing code)
        
        # 2. SwingDetector - uses YOLO poses for phase detection
        detector = SwingDetector()
        phases = detector.detect_swing_phases(poses, fps, hybrik_frames=None)

        # 2.5. MHR Pipeline (Optional) - Extract MHR-70 joints from key frames via SAM-3D
        mhr_data = None
        try:
            from pose.mhr_pipeline import analyze_with_mhr, mhr_result_to_serializable
            from pose.mhr_sam3d_client import is_sam3d_available
            
            if is_sam3d_available():
                print("[MHR] Running SAM-3D MHR analysis on key frames...")
                mhr_data = analyze_with_mhr(
                    video_path=Path(tmp_path),
                    poses=poses,
                    fps=fps,
                    hybrik_frames=hybrik_frames
                )
                
                # Log summary
                success_count = sum(1 for p in mhr_data.values() if p.get("joints3d") is not None)
                print(f"[MHR] Analysis complete: {success_count}/4 phases extracted successfully")
                
                for phase_name, data in mhr_data.items():
                    if data.get("joints3d") is not None:
                        print(f"[MHR] {phase_name}: frame {data['frame']}, joints3d shape {data['joints3d'].shape}")
                    elif data.get("error"):
                        print(f"[MHR] {phase_name}: {data['error']}")
            else:
                print("[MHR] SAM-3D not available, skipping MHR analysis")
        except Exception as e:
            print(f"[MHR] MHR pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            # Continue with normal analysis

        # 3. Metrics - Pass HybrIK frames if available
        calculator = MetricsCalculator()
        metrics = calculator.compute_metrics(poses, phases, fps, hybrik_frames=hybrik_frames)

        # 3.5 Override with MHR 3D metrics when available (more accurate)
        if mhr_data:
            mhr_success = all(mhr_data.get(p, {}).get("joints3d") is not None 
                             for p in ["address", "top", "impact"])
            if mhr_success:
                try:
                    from pose.mhr_metrics import compute_all_mhr_metrics
                    
                    mhr_metrics = compute_all_mhr_metrics(mhr_data, handedness=handedness or "Right")
                    print(f"[MHR] Computed 3D metrics: {list(mhr_metrics.keys())}")
                    
                    # Override existing metrics with MHR values (if not None)
                    for key, value in mhr_metrics.items():
                        if value is not None and hasattr(metrics, key):
                            old_val = getattr(metrics, key)
                            setattr(metrics, key, round(value, 2) if isinstance(value, float) else value)
                            print(f"[MHR] {key}: {old_val} → {round(value, 2) if isinstance(value, float) else value}")
                    
                    print("[MHR] ✓ Metrics updated with 3D MHR data")
                except Exception as e:
                    print(f"[MHR] Failed to compute MHR metrics: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 3.6 Compute extended MHR metrics (finish, sway, plane)
        extended_metrics = {}
        if mhr_data:
            # Try to compute extended metrics even if some phases are missing
            # The individual metric functions handle missing data gracefully
            try:
                from pose.mhr_finish_metrics import compute_finish_metrics
                from pose.mhr_sway_metrics import compute_all_sway_metrics
                from pose.mhr_plane_metrics import compute_swing_plane_metrics
                
                # Finish metrics (needs finish phase)
                if mhr_data.get("finish", {}).get("joints3d") is not None:
                    finish_metrics = compute_finish_metrics(mhr_data, handedness=handedness or "right")
                    extended_metrics.update(finish_metrics)
                    print(f"[MHR] ✓ Finish metrics: {list(finish_metrics.keys())}")
                
                # Sway metrics (can handle partial phases)
                sway_metrics = compute_all_sway_metrics(mhr_data)
                extended_metrics.update(sway_metrics)
                print(f"[MHR] ✓ Sway metrics: {list(sway_metrics.keys())}")
                
                # Swing plane metrics (can handle partial phases)
                plane_metrics = compute_swing_plane_metrics(mhr_data, handedness=handedness or "right")
                extended_metrics.update(plane_metrics)
                print(f"[MHR] ✓ Plane metrics: {list(plane_metrics.keys())}")
                
            except Exception as e:
                print(f"[MHR] Extended metrics failed: {e}")
                import traceback
                traceback.print_exc()

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
        feedback = feedback_service.generate_feedback(metrics, scores, handedness, club_type, db, ref_profile)

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
        print(f"[DEBUG] Saved video to: {saved_video_path}")
        
        # Verify file exists immediately after saving
        abs_saved_path = os.path.abspath(saved_video_path)
        if os.path.exists(abs_saved_path):
            print(f"[DEBUG] Verified video file exists at: {abs_saved_path}, Size: {os.path.getsize(abs_saved_path)} bytes")
        else:
            print(f"[ERROR] Video file MISSING immediately after save at: {abs_saved_path}")
        
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
        
        # Save MHR data to JSON for skeleton visualization
        if mhr_data:
            try:
                mhr_save_data = {}
                for phase_name, data in mhr_data.items():
                    phase_data = {
                        "frame": data.get("frame"),
                    }
                    # Convert numpy arrays to lists
                    if data.get("joints3d") is not None:
                        phase_data["joints3d"] = to_list_safe(data["joints3d"])
                    if data.get("joints2d") is not None:
                        phase_data["joints2d"] = to_list_safe(data["joints2d"])
                    if data.get("error"):
                        phase_data["error"] = data["error"]
                    mhr_save_data[phase_name] = phase_data
                
                mhr_path = os.path.join("videos", f"{db_session.id}_mhr.json")
                
                # Add extended metrics if available (convert numpy types to native Python)
                if extended_metrics:
                    serializable_extended = {}
                    for k, v in extended_metrics.items():
                        if v is None:
                            serializable_extended[k] = None
                        elif isinstance(v, (bool,)):  # Handle bools first since bool is subclass of int
                            serializable_extended[k] = bool(v)
                        elif hasattr(v, 'item'):  # numpy scalar
                            serializable_extended[k] = v.item()
                        elif isinstance(v, (int, float, str)):
                            serializable_extended[k] = v
                        else:
                            serializable_extended[k] = str(v)
                    mhr_save_data["extended_metrics"] = serializable_extended
                
                with open(mhr_path, "w") as f:
                    json.dump(mhr_save_data, f)
                print(f"[MHR] ✓ Saved MHR data to {mhr_path}")
            except Exception as e:
                print(f"[MHR] Failed to save MHR data: {e}")
        
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

    # Load original poses
    poses_path = os.path.join("videos", f"{session_id}_poses.json")
    if not os.path.exists(poses_path):
        return []
        
    import json
    with open(poses_path, "r") as f:
        poses_data = json.load(f)
                
    return poses_data

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
    
    # Delete files
    storage = VideoStorage()
    storage.delete_video(session_id)
    
    # Delete poses JSON
    poses_path = os.path.join("videos", f"{session_id}_poses.json")
    if os.path.exists(poses_path):
        try:
            os.remove(poses_path)
        except OSError:
            pass
            
    # Delete key frame images
    for phase in ["address", "top", "impact", "finish"]:
        img_path = os.path.join("videos", f"{session_id}_{phase}.jpg")
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except OSError:
                pass
                
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
    
    # Load poses from JSON file
    poses_path = os.path.join("videos", f"{session_id}_poses.json")
        
    if not os.path.exists(poses_path):
        return []
    
    import json
    with open(poses_path, "r") as f:
        poses_data = json.load(f)
        
    # NOTE: Blending is now applied during analysis.
    
    # Convert to FramePose format
    from pose.types import FramePose, Point3D
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
    
    # Load MHR data if available (for better skeleton visualization)
    mhr_data = None
    mhr_path = os.path.join("videos", f"{session_id}_mhr.json")
    if os.path.exists(mhr_path):
        try:
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
            # Check if image exists
            image_filename = f"{session_id}_{phase_name}.jpg"
            image_path = os.path.join("videos", image_filename)
            if os.path.exists(image_path):
                kf["image_url"] = f"/api/v1/sessions/{session_id}/frames/{phase_name}"
                
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

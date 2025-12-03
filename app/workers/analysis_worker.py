"""
Background worker for processing video analysis jobs.

Runs as a separate thread, picks jobs from queue, processes them,
and updates the database with results.
"""
import os
import threading
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import traceback

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.job import AnalysisJob, JobStatus
from app.services.job_queue import get_queue, QueueMessage

logger = logging.getLogger(__name__)


class AnalysisWorker:
    """
    Background worker that processes video analysis jobs.
    
    Features:
    - Runs in a separate thread
    - Processes one job at a time
    - Updates job progress in real-time
    - Graceful shutdown support
    """
    
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._hybrik_loaded = False
        
    def start(self):
        """Start the worker thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Worker already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Analysis worker started")
    
    def stop(self, timeout: float = 5.0):
        """Stop the worker thread gracefully."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            logger.info("Analysis worker stopped")
    
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running and self._thread is not None and self._thread.is_alive()
    
    def _run(self):
        """Main worker loop."""
        logger.info("Worker thread started, waiting for jobs...")
        
        # Pre-load HybrIK model
        self._preload_hybrik()
        
        queue = get_queue()
        
        while self._running:
            try:
                # Get next job from queue (blocking with timeout)
                message = queue.dequeue(timeout=1.0)
                
                if message is None:
                    continue
                
                logger.info(f"Processing job {message.job_id}")
                self._process_job(message)
                
                # Mark task as done (for in-memory queue)
                if hasattr(queue, 'task_done'):
                    queue.task_done()
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                traceback.print_exc()
                time.sleep(1)  # Avoid tight loop on persistent errors
    
    def _preload_hybrik(self):
        """Pre-load HybrIK model for faster processing."""
        # Check if HybrIK is disabled via environment variable
        if os.getenv("DISABLE_HYBRIK", "").lower() in ("true", "1", "yes"):
            logger.info("HybrIK disabled via DISABLE_HYBRIK env var")
            self._preload_yolo()  # Pre-load YOLO as fallback
            return
        
        try:
            from pose.smpl_extractor import (
                get_hybrik_extractor,
                is_smpl_available,
                HYBRIK_AVAILABLE
            )
            
            if HYBRIK_AVAILABLE and is_smpl_available():
                logger.info("Pre-loading HybrIK model in worker thread...")
                logger.info("(Set DISABLE_HYBRIK=true in .env to use faster YOLO instead)")
                extractor = get_hybrik_extractor()
                if extractor:
                    success = extractor.load_model()
                    if success:
                        self._hybrik_loaded = True
                        logger.info("✅ HybrIK model loaded in worker")
                    else:
                        logger.warning("⚠️ HybrIK failed to load")
                        self._preload_yolo()  # Pre-load YOLO as fallback
            else:
                logger.info("HybrIK not available")
                self._preload_yolo()  # Pre-load YOLO as fallback
                
        except Exception as e:
            logger.warning(f"HybrIK preload failed: {e}")
            self._preload_yolo()  # Pre-load YOLO as fallback
    
    def _preload_yolo(self):
        """Pre-load YOLO model as fallback."""
        try:
            from pose.yolo_pose_extractor import get_yolo_model, is_yolo_available
            
            if is_yolo_available():
                logger.info("Pre-loading YOLOv8-pose model...")
                model = get_yolo_model()
                if model:
                    logger.info("✅ YOLOv8-pose model loaded")
                else:
                    logger.warning("⚠️ YOLOv8-pose failed to load, using MediaPipe")
            else:
                logger.info("YOLOv8-pose not available, using MediaPipe")
        except Exception as e:
            logger.warning(f"YOLO preload failed: {e}")
    
    def _process_job(self, message: QueueMessage):
        """Process a single analysis job."""
        db = SessionLocal()
        start_time = time.time()
        
        try:
            # Get job from database
            job = db.query(AnalysisJob).filter(AnalysisJob.id == message.job_id).first()
            if not job:
                logger.error(f"Job {message.job_id} not found in database")
                return
            
            # Update status to processing
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            job.current_step = "Initializing..."
            job.progress = 5.0
            db.commit()
            
            # Run the actual analysis
            session_id, pose_method = self._run_analysis(
                db, job, message
            )
            
            # Mark as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.session_id = session_id
            job.pose_method = pose_method
            job.progress = 100.0
            job.current_step = "Complete"
            job.processing_time_ms = (time.time() - start_time) * 1000
            db.commit()
            
            logger.info(f"✅ Job {message.job_id} completed in {job.processing_time_ms:.0f}ms")
            
        except Exception as e:
            logger.error(f"❌ Job {message.job_id} failed: {e}")
            traceback.print_exc()
            
            # Mark as failed
            try:
                job = db.query(AnalysisJob).filter(AnalysisJob.id == message.job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    job.processing_time_ms = (time.time() - start_time) * 1000
                    db.commit()
            except Exception:
                pass
                
        finally:
            db.close()
    
    def _run_analysis(self, db: Session, job: AnalysisJob, message: QueueMessage) -> tuple:
        """
        Run the video analysis pipeline.
        
        Returns: (session_id, pose_method)
        """
        import cv2
        from pathlib import Path
        
        from pose.mediapipe_wrapper import MediaPipeWrapper
        from pose.swing_detection import SwingDetector
        from pose.metrics import MetricsCalculator
        from reference.reference_profiles import get_reference_profile_for
        from reference.scoring import Scorer
        from services.feedback_service import FeedbackService
        from app.services.analysis_repository import AnalysisRepository
        from app.schemas import SwingAnalysisRequest
        from app.models.user import User
        from app.models.db import SwingSession
        
        video_path = Path(message.video_path)
        pose_method = "MediaPipe 2D"
        
        # Update progress
        def update_progress(progress: float, step: str):
            job.progress = progress
            job.current_step = step
            db.commit()
        
        update_progress(10.0, "Reading video...")
        
        # Get FPS
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if fps <= 0:
            fps = 30.0
        
        update_progress(15.0, "Extracting poses...")
        
        # Try HybrIK first (unless disabled)
        hybrik_frames = None
        poses = None
        use_hybrik = self._hybrik_loaded and not os.getenv("DISABLE_HYBRIK", "").lower() in ("true", "1", "yes")
        
        pose_start = time.time()
        if use_hybrik:
            try:
                from pose.smpl_extractor import (
                    get_hybrik_extractor,
                    is_smpl_available,
                    smpl_to_mediapipe_format,
                    HYBRIK_AVAILABLE
                )
            
                if HYBRIK_AVAILABLE and is_smpl_available():
                    logger.info("Using HybrIK 3D pose extraction")
                    extractor = get_hybrik_extractor()
                    if extractor and extractor._loaded:
                        # Process all frames by default for accuracy (impact detection)
                        # Set HYBRIK_FRAME_STEP=2 or higher in .env for faster but less accurate processing
                        frame_step = int(os.getenv("HYBRIK_FRAME_STEP", "1"))
                        hybrik_frames = extractor.extract_video(video_path, frame_step=frame_step)
                        logger.info(f"⏱️ HybrIK extraction took {time.time() - pose_start:.1f}s")
                        
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
                                        visibility=lm["visibility"]
                                    )
                                    for lm in mp_frame["landmarks"]
                                ]
                                pose = FramePose(
                                    frame_index=mp_frame.get("frame_idx", 0),
                                    timestamp_ms=mp_frame.get("timestamp", 0) * 1000.0,
                                    landmarks=landmarks,
                                    smpl_pose=mp_frame.get("smpl_pose").tolist() if mp_frame.get("smpl_pose") is not None else None
                                )
                                poses.append(pose)
                            pose_method = "HybrIK 3D"
                            logger.info(f"HybrIK extracted {len(poses)} frames")
            except Exception as e:
                logger.warning(f"HybrIK extraction failed: {e}")
                hybrik_frames = None
        
        # Fallback to YOLO (faster than MediaPipe, better accuracy)
        if poses is None or len(poses) == 0:
            try:
                from pose.yolo_pose_extractor import extract_pose_frames_yolo, is_yolo_available
                
                if is_yolo_available():
                    logger.info("HybrIK not available, trying YOLOv8-pose...")
                    yolo_frames = extract_pose_frames_yolo(video_path)
                    
                    if yolo_frames:
                        from pose.mediapipe_wrapper import FramePose, Point3D
                        poses = []
                        for yolo_frame in yolo_frames:
                            landmarks = [
                                Point3D(
                                    x=lm["x"],
                                    y=lm["y"],
                                    z=lm["z"],
                                    visibility=lm["visibility"]
                                )
                                for lm in yolo_frame["landmarks"]
                            ]
                            pose = FramePose(
                                frame_index=yolo_frame["frame_index"],
                                timestamp_ms=yolo_frame["timestamp_sec"] * 1000.0,
                                landmarks=landmarks
                            )
                            poses.append(pose)
                        pose_method = "YOLOv8-pose"
                        logger.info(f"YOLO extracted {len(poses)} frames")
            except Exception as e:
                logger.warning(f"YOLO extraction failed: {e}")
        
        # Final fallback to MediaPipe
        if poses is None or len(poses) == 0:
            logger.info("Using MediaPipe 2D pose extraction (final fallback)")
            mp_wrapper = MediaPipeWrapper()
            poses = mp_wrapper.extract_poses_from_video(str(video_path))
            pose_method = "MediaPipe 2D"
            logger.info(f"MediaPipe extracted {len(poses)} frames")
        
        update_progress(50.0, "Detecting swing phases...")
        
        # Swing detection
        phase_start = time.time()
        detector = SwingDetector()
        phases = detector.detect_swing_phases(poses, fps, hybrik_frames=hybrik_frames)
        logger.info(f"⏱️ Swing detection took {time.time() - phase_start:.1f}s")
        
        update_progress(60.0, "Computing metrics...")
        
        # Metrics calculation
        calculator = MetricsCalculator()
        metrics = calculator.compute_metrics(poses, phases, fps, hybrik_frames=hybrik_frames)
        
        # Auto-detect parameters
        handedness = message.handedness
        club_type = message.club_type
        
        if not handedness:
            handedness = calculator.detect_handedness(poses, phases)
        if not club_type:
            club_type = calculator.estimate_club_type(metrics)
        
        update_progress(70.0, "Scoring...")
        
        # Scoring
        ref_profile = get_reference_profile_for(club_type, message.view)
        scorer = Scorer()
        scores = scorer.build_scores(metrics, ref_profile)
        
        update_progress(80.0, "Generating feedback...")
        
        # Feedback (skip if disabled)
        feedback = None
        if os.getenv("DISABLE_FEEDBACK", "").lower() in ("true", "1", "yes"):
            logger.info("Skipping feedback generation (DISABLE_FEEDBACK=true)")
        else:
            feedback_start = time.time()
            feedback_service = FeedbackService()
            feedback = feedback_service.generate_feedback(metrics, scores, handedness, club_type, ref_profile)
            logger.info(f"⏱️ Feedback generation took {time.time() - feedback_start:.1f}s")
        
        update_progress(90.0, "Saving results...")
        
        # Save to database
        repo = AnalysisRepository(db)
        
        # Get user
        user = db.query(User).filter(User.id == message.user_id).first()
        
        # Save session
        db_session = repo.save_analysis(
            metadata=SwingAnalysisRequest(handedness=handedness, view=message.view, club_type=club_type),
            metrics=metrics,
            phases=phases,
            scores=scores,
            feedback=feedback,
            user_id=message.user_id,
        )
        
        # Check for personal best (after saving to have session ID)
        max_score_session = db.query(SwingSession).filter(
            SwingSession.user_id == message.user_id,
            SwingSession.club_type == club_type,
            SwingSession.view == message.view,
            SwingSession.id != db_session.id  # Exclude current session
        ).order_by(SwingSession.overall_score.desc()).first()
        
        if not max_score_session or scores.overall_score > max_score_session.overall_score:
            db_session.is_personal_best = True
            if max_score_session and max_score_session.is_personal_best:
                max_score_session.is_personal_best = False
                db.add(max_score_session)
            db.add(db_session)
            db.commit()
        
        # Save video
        from app.services.video_storage import VideoStorage
        video_storage = VideoStorage()
        video_storage.save_video(str(video_path), db_session.id)
        
        # Extract and save key frame images
        try:
            # Use absolute path for reliability
            saved_video_path = str(video_storage.get_video_path(db_session.id))
            abs_video_path = os.path.abspath(saved_video_path)
            logger.info(f"📸 Extracting key frame images from {abs_video_path}...")
            
            cap = cv2.VideoCapture(abs_video_path)
            
            # Fallback to original video path if saved video fails to open
            if not cap.isOpened():
                logger.warning(f"❌ Failed to open saved video: {abs_video_path}")
                logger.info(f"🔄 Falling back to original file: {video_path}")
                cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error("❌ Failed to open video file (both saved and original failed)")
            else:
                # Map phase name to frame index
                key_frame_indices = {
                    "address": phases.address_frame,
                    "top": phases.top_frame,
                    "impact": phases.impact_frame,
                    "finish": phases.finish_frame
                }
                
                for phase_name, frame_idx in key_frame_indices.items():
                    if frame_idx is not None and frame_idx >= 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                        ret, frame = cap.read()
                        if ret:
                            # Save image
                            image_filename = f"{db_session.id}_{phase_name}.jpg"
                            image_path = Path("videos") / image_filename
                            cv2.imwrite(str(image_path), frame)
                            logger.info(f"✅ Saved {phase_name} image to {image_path}")
                        else:
                            logger.warning(f"⚠️ Could not read frame {frame_idx} for {phase_name}")
                
                cap.release()
        except Exception as e:
            logger.error(f"❌ Failed to extract key frame images: {e}")
            traceback.print_exc()
        
        # Save poses for skeleton visualization
        import json
        poses_path = Path("videos") / f"{db_session.id}_poses.json"
        poses_data = [
            {
                "frame_index": pose.frame_index,
                "timestamp_ms": pose.timestamp_ms,
                "landmarks": [
                    {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                    for lm in pose.landmarks
                ],
                "smpl_pose": pose.smpl_pose
            }
            for pose in poses
        ]
        with open(poses_path, "w") as f:
            json.dump(poses_data, f)
        logger.info(f"Saved {len(poses_data)} poses to {poses_path}")
        
        return db_session.id, pose_method


# Global worker instance
_worker: Optional[AnalysisWorker] = None


def get_worker() -> AnalysisWorker:
    """Get the global worker instance."""
    global _worker
    if _worker is None:
        _worker = AnalysisWorker()
    return _worker


def start_worker():
    """Start the global worker."""
    worker = get_worker()
    if not worker.is_running():
        worker.start()


def stop_worker():
    """Stop the global worker."""
    global _worker
    if _worker is not None:
        _worker.stop()


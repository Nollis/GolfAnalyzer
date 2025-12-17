from sqlalchemy.orm import Session
from app.models.db import SwingSession, SwingMetric, SwingPhase, SwingFeedbackDB, ReferenceProfileDB
from app.schemas import SwingMetrics, SwingPhases, SwingScores, SwingFeedback, SwingAnalysisRequest, ReferenceProfileCreate
from reference.reference_profiles import MetricTarget

class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_analysis(self, metadata: SwingAnalysisRequest, metrics: SwingMetrics, 
                     phases: SwingPhases, scores: SwingScores, feedback: SwingFeedback,
                     video_path: str = None, user_id: str = None) -> SwingSession:
        # Create Session
        db_session = SwingSession(
            handedness=metadata.handedness,
            view=metadata.view,
            club_type=metadata.club_type,
            video_url=video_path,
            overall_score=scores.overall_score,
            user_id=user_id
        )
        self.db.add(db_session)
        self.db.flush()  # Get the ID

        # Create Metrics - explicitly map all fields to ensure they're saved
        metrics_dict = metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics.dict()
        db_metrics = SwingMetric(
            session_id=db_session.id,
            tempo_ratio=metrics_dict.get('tempo_ratio'),
            backswing_duration_ms=metrics_dict.get('backswing_duration_ms'),
            downswing_duration_ms=metrics_dict.get('downswing_duration_ms'),
            # New metrics (10 core metrics)
            chest_turn_top_deg=metrics_dict.get('chest_turn_top_deg'),
            pelvis_turn_top_deg=metrics_dict.get('pelvis_turn_top_deg'),
            x_factor_top_deg=metrics_dict.get('x_factor_top_deg'),
            spine_angle_address_deg=metrics_dict.get('spine_angle_address_deg'),
            spine_angle_impact_deg=metrics_dict.get('spine_angle_impact_deg'),
            lead_arm_address_deg=metrics_dict.get('lead_arm_address_deg'),
            lead_arm_top_deg=metrics_dict.get('lead_arm_top_deg'),
            lead_arm_impact_deg=metrics_dict.get('lead_arm_impact_deg'),
            trail_elbow_address_deg=metrics_dict.get('trail_elbow_address_deg'),
            trail_elbow_top_deg=metrics_dict.get('trail_elbow_top_deg'),
            trail_elbow_impact_deg=metrics_dict.get('trail_elbow_impact_deg'),
            knee_flex_left_address_deg=metrics_dict.get('knee_flex_left_address_deg'),
            knee_flex_right_address_deg=metrics_dict.get('knee_flex_right_address_deg'),
            head_sway_range=metrics_dict.get('head_sway_range'),
            early_extension_amount=metrics_dict.get('early_extension_amount'),
            swing_path_index=metrics_dict.get('swing_path_index'),
            hand_height_at_top_index=metrics_dict.get('hand_height_at_top_index'),
            hand_width_at_top_index=metrics_dict.get('hand_width_at_top_index'),
            head_drop_cm=metrics_dict.get('head_drop_cm'),
            head_rise_cm=metrics_dict.get('head_rise_cm'),
            # Backward compatibility (old field names)
            shoulder_turn_top_deg=metrics_dict.get('shoulder_turn_top_deg'),
            hip_turn_top_deg=metrics_dict.get('hip_turn_top_deg'),
            spine_tilt_address_deg=metrics_dict.get('spine_tilt_address_deg'),
            spine_tilt_impact_deg=metrics_dict.get('spine_tilt_impact_deg'),
            head_movement_forward_cm=metrics_dict.get('head_movement_forward_cm'),
            head_movement_vertical_cm=metrics_dict.get('head_movement_vertical_cm'),
            shaft_lean_impact_deg=metrics_dict.get('shaft_lean_impact_deg'),
            lead_wrist_flexion_address_deg=metrics_dict.get('lead_wrist_flexion_address_deg'),
            lead_wrist_flexion_top_deg=metrics_dict.get('lead_wrist_flexion_top_deg'),
            lead_wrist_flexion_impact_deg=metrics_dict.get('lead_wrist_flexion_impact_deg'),
            lead_wrist_hinge_top_deg=metrics_dict.get('lead_wrist_hinge_top_deg'),
        )
        self.db.add(db_metrics)

        # Create Phases
        db_phases = SwingPhase(
            session_id=db_session.id,
            **phases.dict()
        )
        self.db.add(db_phases)

        # Create Feedback (if provided)
        if feedback:
            db_feedback = SwingFeedbackDB(
                session_id=db_session.id,
                summary=feedback.summary,
                priority_issues=feedback.priority_issues,
                drills=[d.dict() for d in feedback.drills],
                phase_feedback=feedback.phase_feedback
            )
            self.db.add(db_feedback)

        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def get_session(self, session_id: str) -> SwingSession:
        return self.db.query(SwingSession).filter(SwingSession.id == session_id).first()

    def list_sessions(self, limit: int = 50):
        return self.db.query(SwingSession).order_by(SwingSession.created_at.desc()).limit(limit).all()

    def delete_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False

    def create_reference_profile(self, data: ReferenceProfileCreate) -> ReferenceProfileDB:
        # Convert metrics to targets with +/- 10% tolerance
        targets = {}
        metrics_dict = data.metrics.dict()
        
        for key, val in metrics_dict.items():
            # Simple heuristic: +/- 10% or +/- 5 units if val is small
            # Let's use 10% for now
            min_val = val * 0.9
            max_val = val * 1.1
            
            # Handle negative values (e.g. head movement)
            if min_val > max_val:
                min_val, max_val = max_val, min_val
                
            targets[key] = {
                "min_val": min_val,
                "max_val": max_val,
                "ideal_val": val,
                "weight": 1.0 # Default weight
            }
            
        profile = ReferenceProfileDB(
            name=data.name,
            targets=targets,
            is_default=0
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def list_reference_profiles(self):
        return self.db.query(ReferenceProfileDB).all()

    def get_reference_profile(self, profile_id: str) -> ReferenceProfileDB:
        return self.db.query(ReferenceProfileDB).filter(ReferenceProfileDB.id == profile_id).first()

    def unset_personal_best(self, club_type: str, view: str):
        """Unset is_personal_best for all sessions with matching criteria"""
        self.db.query(SwingSession).filter(
            SwingSession.club_type == club_type,
            SwingSession.view == view,
            SwingSession.is_personal_best == True
        ).update({"is_personal_best": False})
        self.db.commit()

    def get_personal_best(self, club_type: str, view: str) -> SwingSession:
        return self.db.query(SwingSession).filter(
            SwingSession.club_type == club_type,
            SwingSession.view == view,
            SwingSession.is_personal_best == True
        ).first()

    def get_recent_swings(
        self, 
        user_id: str, 
        club_type: str = None, 
        limit: int = 5
    ) -> list:
        """
        Get recent swings for a user, optionally filtered by club type.
        
        Args:
            user_id: User's ID
            club_type: Optional club type filter (e.g., 'driver', 'iron')
            limit: Maximum number of swings to return
        
        Returns:
            List of SwingSession objects, newest first.
        """
        query = self.db.query(SwingSession).filter(
            SwingSession.user_id == user_id
        )
        
        if club_type:
            query = query.filter(SwingSession.club_type == club_type)
        
        return query.order_by(
            SwingSession.created_at.desc()
        ).limit(limit).all()

    def get_recent_metrics(
        self, 
        user_id: str, 
        club_type: str = None, 
        limit: int = 5
    ) -> list:
        """
        Get recent swing metrics as dictionaries for improvement delta calculation.
        
        Returns list of metric dicts, newest first.
        """
        sessions = self.get_recent_swings(user_id, club_type, limit)
        result = []
        
        for session in sessions:
            if session.metrics:
                # Convert ORM object to dict
                metrics_dict = {}
                for col in session.metrics.__table__.columns:
                    if col.name not in ['id', 'session_id']:
                        val = getattr(session.metrics, col.name)
                        if val is not None:
                            metrics_dict[col.name] = val
                result.append(metrics_dict)
        
        return result

    def save_feedback(self, session_id: str, feedback: SwingFeedback) -> SwingFeedbackDB:
        """
        Save or update feedback for a session.
        """
        # Check if feedback already exists
        db_feedback = self.db.query(SwingFeedbackDB).filter(SwingFeedbackDB.session_id == session_id).first()
        
        if db_feedback:
            # Update existing
            db_feedback.summary = feedback.summary
            db_feedback.priority_issues = feedback.priority_issues
            db_feedback.drills = [d.dict() for d in feedback.drills]
            db_feedback.phase_feedback = feedback.phase_feedback
        else:
            # Create new
            db_feedback = SwingFeedbackDB(
                session_id=session_id,
                summary=feedback.summary,
                priority_issues=feedback.priority_issues,
                drills=[d.dict() for d in feedback.drills],
                phase_feedback=feedback.phase_feedback
            )
            self.db.add(db_feedback)
            
        with open("debug_log.txt", "a") as f:
            f.write(f"DEBUG: Saving feedback for {session_id}\n")
            f.write(f"DEBUG: Feedback data: {feedback.dict()}\n")
            f.write(f"DEBUG: Phase feedback to save: {feedback.phase_feedback}\n")
            
        self.db.commit()
        self.db.refresh(db_feedback)
        
        with open("debug_log.txt", "a") as f:
             f.write(f"DEBUG: Saved DB Feedback ID: {db_feedback.id}\n")
             f.write(f"DEBUG: Saved DB Phase Feedback: {db_feedback.phase_feedback}\n")

        return db_feedback

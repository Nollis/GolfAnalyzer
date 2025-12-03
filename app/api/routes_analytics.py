from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.api.deps import get_db, get_current_active_user
from app.models.db import SwingSession
from app.models.user import User
from app.schemas import DashboardStats, TrendResponse, TrendPoint, ComparisonResponse, MetricDiff

router = APIRouter()

@router.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Base query for user's sessions
    base_query = db.query(SwingSession).filter(SwingSession.user_id == current_user.id)
    
    # Total sessions
    total_sessions = base_query.count()
    
    # Average score
    avg_score = base_query.with_entities(func.avg(SwingSession.overall_score)).scalar() or 0.0
    
    # Last session date
    last_session = base_query.order_by(SwingSession.created_at.desc()).first()
    last_session_date = last_session.created_at if last_session else None
    
    # Personal Bests per club type
    # We want the max score for each club type
    # This can be done with a group by query
    pb_query = db.query(
        SwingSession.club_type,
        func.max(SwingSession.overall_score)
    ).filter(
        SwingSession.user_id == current_user.id
    ).group_by(SwingSession.club_type).all()
    
    personal_bests = {club: score for club, score in pb_query}
    
    # Ensure all types are present (optional, but good for UI)
    for club in ["driver", "iron", "wedge"]:
        if club not in personal_bests:
            personal_bests[club] = None

    return DashboardStats(
        total_sessions=total_sessions,
        average_score=round(avg_score, 1),
        last_session_date=last_session_date,
        personal_bests=personal_bests
    )

@router.get("/trends", response_model=List[TrendResponse])
def get_trends(
    club_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(SwingSession).filter(SwingSession.user_id == current_user.id)
    
    if club_type:
        query = query.filter(SwingSession.club_type == club_type)
        
    # Get recent sessions ordered by date
    sessions = query.order_by(SwingSession.created_at.asc()).limit(limit).all()
    
    # Group by club type
    trends_by_club = {}
    
    for s in sessions:
        if s.club_type not in trends_by_club:
            trends_by_club[s.club_type] = []
            
        # Extract key metrics
        metrics = {
            "tempo_ratio": s.metrics.get("tempo_ratio", 0),
            "shoulder_turn": s.metrics.get("shoulder_turn_top_deg", 0),
            "hip_turn": s.metrics.get("hip_turn_top_deg", 0)
        }
        
        trends_by_club[s.club_type].append(TrendPoint(
            date=s.created_at,
            score=s.overall_score,
            metrics=metrics
        ))
        
    return [
        TrendResponse(club_type=club, data=points)
        for club, points in trends_by_club.items()
    ]

@router.get("/comparison", response_model=ComparisonResponse)
def compare_sessions(
    session_id_1: str,
    session_id_2: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    s1 = db.query(SwingSession).filter(SwingSession.session_id == session_id_1, SwingSession.user_id == current_user.id).first()
    s2 = db.query(SwingSession).filter(SwingSession.session_id == session_id_2, SwingSession.user_id == current_user.id).first()
    
    if not s1 or not s2:
        raise HTTPException(status_code=404, detail="One or both sessions not found")
        
    # Calculate metric diffs
    diffs = []
    
    # Overall Score
    score_diff = s2.overall_score - s1.overall_score
    diffs.append(MetricDiff(
        metric_name="Overall Score",
        session_1_value=s1.overall_score,
        session_2_value=s2.overall_score,
        diff=score_diff,
        improvement=score_diff > 0
    ))
    
    # Common metrics to compare
    common_metrics = [
        ("tempo_ratio", "Tempo Ratio", 3.0), # Target 3.0
        ("shoulder_turn_top_deg", "Shoulder Turn", 90.0), # Target ~90
        ("hip_turn_top_deg", "Hip Turn", 45.0) # Target ~45
    ]
    
    for key, name, target in common_metrics:
        v1 = s1.metrics.get(key, 0)
        v2 = s2.metrics.get(key, 0)
        diff = v2 - v1
        
        # Improvement logic depends on metric. 
        # For now, let's assume closer to target is better? 
        # Or just simple diff? Let's do simple diff and simple improvement check
        # For tempo, closer to 3.0 is better.
        if key == "tempo_ratio":
            dist1 = abs(v1 - target)
            dist2 = abs(v2 - target)
            improvement = dist2 < dist1
        else:
            # For turns, usually more is better up to a point, but let's just say higher is "improvement" for simplicity
            # or maybe we just mark it as improvement if it increased?
            improvement = diff > 0
            
        diffs.append(MetricDiff(
            metric_name=name,
            session_1_value=v1,
            session_2_value=v2,
            diff=diff,
            improvement=improvement
        ))
        
    return ComparisonResponse(
        session_1=s1,
        session_2=s2,
        metrics=diffs
    )

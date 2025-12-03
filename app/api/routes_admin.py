from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.db import SwingSession
from app.schemas import UserResponse
from typing import List
from datetime import datetime, timedelta

router = APIRouter()

def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency to ensure current user is an admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Admin access required."
        )
    return current_user

@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get specific user details (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Toggle user active status (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin and user.id != admin.id:
        raise HTTPException(status_code=403, detail="Cannot deactivate other admins")
    
    user.is_active = not user.is_active
    db.commit()
    return {"status": "success", "is_active": user.is_active}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Delete a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete admin users")
    
    # Delete user's sessions first
    db.query(SwingSession).filter(SwingSession.user_id == user_id).delete()
    
    # Delete user
    db.delete(user)
    db.commit()
    return {"status": "success"}

@router.get("/analytics/platform-stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get platform-wide analytics (admin only)"""
    
    # Total users
    total_users = db.query(func.count(User.id)).scalar()
    
    # Active users (logged in last 30 days - we'd need a last_login field for this)
    # For now, just count users with sessions in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.query(func.count(func.distinct(SwingSession.user_id))).filter(
        SwingSession.created_at >= thirty_days_ago
    ).scalar()
    
    # Total sessions
    total_sessions = db.query(func.count(SwingSession.id)).scalar()
    
    # Sessions by club type
    sessions_by_club = db.query(
        SwingSession.club_type,
        func.count(SwingSession.id).label('count')
    ).group_by(SwingSession.club_type).all()
    
    # Recent registrations (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_registrations = db.query(func.count(User.id)).filter(
        User.created_at >= seven_days_ago
    ).scalar()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_sessions": total_sessions,
        "sessions_by_club_type": {club: count for club, count in sessions_by_club},
        "recent_registrations": recent_registrations
    }

@router.get("/analytics/user-activity")
def get_user_activity(
    days: int = 30,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Get user activity over time (admin only)"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Sessions per day
    daily_sessions = db.query(
        func.date(SwingSession.created_at).label('date'),
        func.count(SwingSession.id).label('count')
    ).filter(
        SwingSession.created_at >= cutoff_date
    ).group_by(
        func.date(SwingSession.created_at)
    ).order_by(
        func.date(SwingSession.created_at)
    ).all()
    
    return {
        "daily_sessions": [
            {"date": str(date), "count": count}
            for date, count in daily_sessions
        ]
    }

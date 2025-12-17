from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.deps import get_db, get_current_active_user
from app.models.drill import Drill
from app.models.user import User
from app.schemas import DrillResponse, DrillCreate

router = APIRouter()

@router.get("/", response_model=List[DrillResponse])
def list_drills(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    target_metric: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Drill)
    
    if category:
        query = query.filter(Drill.category == category)
    if difficulty:
        query = query.filter(Drill.difficulty == difficulty)
    if target_metric:
        query = query.filter(Drill.target_metric == target_metric)
    if q:
        search = f"%{q}%"
        from sqlalchemy import or_
        query = query.filter(or_(Drill.title.ilike(search), Drill.description.ilike(search)))
        
    return query.all()

@router.get("/{drill_id}", response_model=DrillResponse)
def get_drill(
    drill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    drill = db.query(Drill).filter(Drill.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    return drill

@router.post("/", response_model=DrillResponse, status_code=status.HTTP_201_CREATED)
def create_drill(
    drill_in: DrillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    drill = Drill(**drill_in.dict())
    db.add(drill)
    db.commit()
    db.refresh(drill)
    return drill

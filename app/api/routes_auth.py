from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models.user import User
from app.models.credits import Credits
from app.schemas import UserCreate, UserResponse, Token, UserUpdate
from app.api.deps import get_current_active_user

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        handicap=user.handicap,
        handedness=user.handedness,
        height_cm=user.height_cm,
        age=user.age,
        auth_provider="local"
    )
    db.add(new_user)
    db.flush() # Flush to get ID
    
    # Create default credits
    new_credits = Credits(user_id=new_user.id, free_credits_remaining=5)
    db.add(new_credits)
    
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user's profile"""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.handicap is not None:
        current_user.handicap = user_update.handicap
    if user_update.handedness is not None:
        current_user.handedness = user_update.handedness
    if user_update.height_cm is not None:
        current_user.height_cm = user_update.height_cm
    if user_update.age is not None:
        current_user.age = user_update.age
    
    db.commit()
    db.refresh(current_user)
    return current_user

# --- Phase 2A: "Real Enough" Auth ---

from pydantic import BaseModel, EmailStr

class EmailRequest(BaseModel):
    email: EmailStr

@router.post("/verify-email")
def verify_email(request: EmailRequest):
    """
    Mock Email Verification.
    In prod, this would send an email with a link.
    """
    print(f"📧 [MOCK EMAIL] Sending verification email to {request.email}")
    return {"message": "Verification email sent (Simulated)"}

@router.post("/request-reset")
def request_password_reset(request: EmailRequest, db: Session = Depends(get_db)):
    """
    Mock Password Reset.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal user existence
        return {"message": "If this email is registered, a reset link has been sent."}
    
    # Generate a fake token
    import uuid
    token = str(uuid.uuid4())
    print(f"🔑 [MOCK RESET] Password reset token for {request.email}: {token}")
    print(f"👉 Link: http://localhost:5173/reset-password?token={token}")
    
    return {"message": "If this email is registered, a reset link has been sent."}


# --- Google OAuth (Skeleton methods) ---
# In a real app, use authlib or raw implementation with client_id/secret env vars

@router.get("/login/google")
def login_google():
    """
    Initiates Google OAuth flow.
    """
    return {"message": "Google Login not fully configured yet. Needs Client ID."}

@router.get("/login/google/callback")
def login_google_callback(code: str):
    """
    Callback from Google.
    Creates user if not exists (auth_provider='google').
    Returns JWT.
    """
    return {"message": f"Received code {code}. Implementation pending."}

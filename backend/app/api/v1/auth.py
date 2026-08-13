from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.db.models import Civilian, TrafficController, User
import hashlib

router = APIRouter()

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    user_type: str = "civilian"  # "civilian" or "controller"
    full_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str
    user_type: str = "civilian"

class GoogleSyncRequest(BaseModel):
    email: str
    full_name: Optional[str] = None
    user_type: str = "civilian"

class AuthResponse(BaseModel):
    success: bool
    message: str
    user_type: Optional[str] = None
    email: Optional[str] = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_default_controller(db: Session):
    """Seed default Traffic Controller account if not present."""
    default_email = "trafficcontroller@gmail.com"
    default_pwd_hash = hash_password("trafficcontroller01")
    
    existing = db.query(TrafficController).filter(TrafficController.email == default_email).first()
    if not existing:
        new_controller = TrafficController(
            email=default_email,
            hashed_password=default_pwd_hash,
            full_name="Head Traffic Controller",
            badge_number="TC-MASTER-01"
        )
        db.add(new_controller)
        db.commit()

@router.post("/register", response_model=AuthResponse)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new Civilian or Traffic Controller in separate Supabase tables."""
    email_clean = request.email.strip().lower()
    hashed_pwd = hash_password(request.password)

    if request.user_type == "controller":
        existing = db.query(TrafficController).filter(TrafficController.email == email_clean).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Traffic Controller account already exists with this email."
            )
        new_user = TrafficController(
            email=email_clean,
            hashed_password=hashed_pwd,
            full_name=request.full_name or email_clean.split('@')[0]
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return AuthResponse(
            success=True,
            message="Traffic Controller registered successfully in database!",
            user_type="controller",
            email=new_user.email
        )
    else:
        existing = db.query(Civilian).filter(Civilian.email == email_clean).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Civilian account already exists with this email."
            )
        new_user = Civilian(
            email=email_clean,
            hashed_password=hashed_pwd,
            full_name=request.full_name or email_clean.split('@')[0],
            auth_provider="credentials"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return AuthResponse(
            success=True,
            message="Civilian registered successfully in database!",
            user_type="civilian",
            email=new_user.email
        )

@router.post("/login", response_model=AuthResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates user from respective Civilian or TrafficController table."""
    init_default_controller(db)
    email_clean = request.email.strip().lower()
    hashed_pwd = hash_password(request.password)

    if request.user_type == "controller":
        controller = db.query(TrafficController).filter(TrafficController.email == email_clean).first()
        if not controller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Traffic Controller account not found."
            )
        if controller.hashed_password != hashed_pwd:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials for Traffic Controller."
            )
        return AuthResponse(
            success=True,
            message="Traffic Controller authenticated successfully!",
            user_type="controller",
            email=controller.email
        )
    else:
        civilian = db.query(Civilian).filter(Civilian.email == email_clean).first()
        if not civilian:
            # Fallback search in User table
            user = db.query(User).filter(User.email == email_clean).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Civilian account not found. Please register first."
                )
            if user.hashed_password != hashed_pwd:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials."
                )
            return AuthResponse(
                success=True,
                message="Login successful!",
                user_type="civilian",
                email=user.email
            )
        if civilian.hashed_password and civilian.hashed_password != hashed_pwd:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials."
            )
        return AuthResponse(
            success=True,
            message="Civilian authenticated successfully!",
            user_type="civilian",
            email=civilian.email
        )

@router.post("/google-sync", response_model=AuthResponse)
def google_sync(request: GoogleSyncRequest, db: Session = Depends(get_db)):
    """Stores/syncs Google OAuth signed-in user into Civilians database table."""
    email_clean = request.email.strip().lower()
    civilian = db.query(Civilian).filter(Civilian.email == email_clean).first()
    
    if not civilian:
        civilian = Civilian(
            email=email_clean,
            full_name=request.full_name or email_clean.split('@')[0],
            auth_provider="google"
        )
        db.add(civilian)
        db.commit()
        db.refresh(civilian)
        msg = "Google signed-in user saved to Civilians table."
    else:
        msg = "Google user synced with Civilians database."

    return AuthResponse(
        success=True,
        message=msg,
        user_type="civilian",
        email=civilian.email
    )

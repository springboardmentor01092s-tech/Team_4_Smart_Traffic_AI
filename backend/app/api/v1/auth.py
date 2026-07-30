from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.database import get_db
from app.db.models import User
import hashlib

router = APIRouter()

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    user_type: str = "civilian" # "civilian" or "controller"
    full_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str
    user_type: str = "civilian"

class AuthResponse(BaseModel):
    success: bool
    message: str
    user_type: Optional[str] = None
    email: Optional[str] = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@router.post("/register", response_model=AuthResponse)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user in Supabase database."""
    email_clean = request.email.strip().lower()
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists with this email. Please sign in."
        )

    # Create new user in Supabase
    hashed_pwd = hash_password(request.password)
    new_user = User(
        email=email_clean,
        hashed_password=hashed_pwd,
        user_type=request.user_type,
        full_name=request.full_name or email_clean.split('@')[0]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return AuthResponse(
        success=True,
        message="Account registered successfully in Supabase database!",
        user_type=new_user.user_type,
        email=new_user.email
    )

@router.post("/login", response_model=AuthResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates an existing user from Supabase database."""
    email_clean = request.email.strip().lower()
    
    # Find user in database
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found. You do not have an account yet — please register/sign up first."
        )

    # Check password
    hashed_pwd = hash_password(request.password)
    if user.hashed_password != hashed_pwd:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Password does not match."
        )

    return AuthResponse(
        success=True,
        message="Login successful!",
        user_type=user.user_type,
        email=user.email
    )

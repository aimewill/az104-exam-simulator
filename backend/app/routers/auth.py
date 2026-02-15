"""API routes for user authentication."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    require_auth,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    created_at: Optional[str] = None


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Validate password
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )
    
    # Create user
    user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        display_name=request.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    token = create_access_token(user.id, user.email)
    
    return TokenResponse(
        access_token=token,
        user=user.to_dict(),
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and get an access token."""
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Generate token
    token = create_access_token(user.id, user.email)
    
    return TokenResponse(
        access_token=token,
        user=user.to_dict(),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(user: User = Depends(require_auth)):
    """Get the current authenticated user's information."""
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name or user.email.split("@")[0],
        created_at=user.created_at.isoformat() if user.created_at else None,
    )

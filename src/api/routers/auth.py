"""
Phase 7.2 — Auth Router
Endpoints: /auth/register, /auth/login, /auth/refresh, /auth/me, /auth/logout
Added Phase 10: /verify-email, /forgot-password, /reset-password
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..models.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from ..db.models import User, get_db
from ..db.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_by_verification_token,
    get_user_by_reset_token,
    generate_random_token,
    hash_password,
)
from ..db.dependencies import get_current_user
from ..services.email_service import send_verification_email, send_password_reset_email

logger = logging.getLogger("securehall-rag")
router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new employee account (role=employee by default)."""
    if get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    if get_user_by_username(db, body.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")

    user = create_user(
        db,
        email=body.email,
        username=body.username,
        password=body.password,
        full_name=body.full_name,
        role="employee",
    )
    logger.info(f"New user registered: {user.email} ({user.role}). Verification bypassed.")
    
    # Auto-login: return tokens immediately (verification disabled for now)
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access, refresh_token=refresh, user=_user_to_dict(user)
    )


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify an email address using the token sent via email."""
    user = get_user_by_verification_token(db, body.token)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification token")
    
    user.is_verified = True
    user.verification_token = None
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User verified: {user.email}")
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login with email + password. Returns JWT access + refresh tokens."""
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # if not user.is_verified:
    #     raise HTTPException(
    #         status.HTTP_403_FORBIDDEN,
    #         "Account not verified. Please check your email for the verification link."
    #     )

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    logger.info(f"User logged in: {user.email} from {request.client.host}")
    return TokenResponse(
        access_token=access, refresh_token=refresh, user=_user_to_dict(user)
    )


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset link."""
    user = get_user_by_email(db, body.email)
    if not user:
        # Prevent email enumeration by returning success anyway
        return {"message": "If that email is registered, a password reset link has been sent."}
    
    user.reset_password_token = generate_random_token()
    user.reset_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    send_password_reset_email(user.email, user.reset_password_token)
    
    return {"message": "If that email is registered, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using the token sent via email."""
    user = get_user_by_reset_token(db, body.token)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid password reset token")
        
    if user.reset_password_expires_at and datetime.utcnow() > user.reset_password_expires_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password reset token has expired")
        
    user.hashed_password = hash_password(body.new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Password reset successful for user: {user.email}")
    return {"message": "Password has been reset successfully. You can now log in."}


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Exchange a refresh token for a new access token."""
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = get_user_by_id(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
        
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account not verified")

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access, refresh_token=refresh, user=_user_to_dict(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently logged-in user profile."""
    return current_user


@router.post("/logout")
async def logout():
    """
    Client-side logout: the client drops its JWTs.
    In a stateless JWT setup, no server action is required unless using a token blocklist.
    """
    return {"message": "Logged out successfully"}

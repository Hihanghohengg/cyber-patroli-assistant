"""Authentication endpoints for Web Dashboard."""

import time
import logging
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intelligence import DashboardUser
from app.models.audit import AuditLog
from app.auth.jwt_handler import verify_password, hash_password, create_access_token
from app.auth.dependencies import get_current_user, require_role, seed_default_admin_if_needed
from app.schemas.dashboard import LoginRequest, RegisterUserRequest, TokenResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Dashboard Auth"])

# Rate Limiter & Brute-Force Defense: max 5 failed attempts per 5 minutes per IP
_FAILED_LOGIN_ATTEMPTS = defaultdict(list)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes


def _enforce_rate_limit(client_ip: str):
    now = time.time()
    # Expire old records outside the lockout window
    _FAILED_LOGIN_ATTEMPTS[client_ip] = [
        t for t in _FAILED_LOGIN_ATTEMPTS[client_ip] if now - t < LOCKOUT_DURATION_SECONDS
    ]
    if len(_FAILED_LOGIN_ATTEMPTS[client_ip]) >= MAX_FAILED_ATTEMPTS:
        lockout_remaining = int(LOCKOUT_DURATION_SECONDS - (now - _FAILED_LOGIN_ATTEMPTS[client_ip][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Terlalu banyak percobaan login gagal. Akses ditolak sementara selama {max(1, lockout_remaining)} detik demi keamanan.",
        )


def _record_failed_attempt(client_ip: str):
    _FAILED_LOGIN_ATTEMPTS[client_ip].append(time.time())


def _clear_failed_attempts(client_ip: str):
    _FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate dashboard analyst/admin and issue JWT bearer token."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    _enforce_rate_limit(client_ip)

    # Ensure default admin is created if table is empty
    seed_default_admin_if_needed(db)

    user = db.query(DashboardUser).filter(DashboardUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        _record_failed_attempt(client_ip)
        try:
            audit = AuditLog(
                action="AUTH_LOGIN_FAILED",
                actor_username=payload.username,
                entity_type="DashboardUser",
                entity_id=str(user.user_id) if user else None,
                details={
                    "reason": "Invalid credentials",
                    "attempted_username": payload.username,
                    "account_exists": user is not None,
                },
                ip_address=client_ip,
                timestamp=datetime.utcnow(),
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning("Failed to record failed login audit: %s", e)
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nama pengguna atau kata sandi tidak sesuai",
        )

    # Clear failed counters on successful authentication
    _clear_failed_attempts(client_ip)

    if not user.is_active:
        try:
            audit = AuditLog(
                action="AUTH_LOGIN_BLOCKED",
                actor_username=user.username,
                entity_type="DashboardUser",
                entity_id=str(user.user_id),
                details={"reason": "Account is inactive"},
                ip_address=client_ip,
                timestamp=datetime.utcnow(),
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning("Failed to record blocked login audit: %s", e)
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun ini telah dinonaktifkan oleh Administrator",
        )

    # Update last login time & Record Success Audit Log
    user.last_login_at = datetime.utcnow()
    try:
        audit = AuditLog(
            action="AUTH_LOGIN_SUCCESS",
            actor_username=user.username,
            entity_type="DashboardUser",
            entity_id=str(user.user_id),
            details={"role": user.role},
            ip_address=client_ip,
            timestamp=datetime.utcnow(),
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.warning("Failed to record successful login audit: %s", e)
        db.commit()

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": str(user.user_id)}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: DashboardUser = Depends(get_current_user)):
    """Return currently authenticated analyst profile."""
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse)
def register_user(
    payload: RegisterUserRequest,
    request: Request,
    admin_user: DashboardUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to create new analyst accounts."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    if db.query(DashboardUser).filter(DashboardUser.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama pengguna sudah terdaftar",
        )

    role_val = (payload.role or "ANALYST").upper()
    new_user = DashboardUser(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name or "",
        role=role_val,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    try:
        audit = AuditLog(
            action="AUTH_USER_REGISTERED",
            actor_username=admin_user.username,
            entity_type="DashboardUser",
            entity_id=str(new_user.user_id),
            details={
                "created_username": new_user.username,
                "role": new_user.role,
                "full_name": new_user.full_name,
                "created_by": admin_user.username,
            },
            ip_address=client_ip,
            timestamp=datetime.utcnow(),
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.warning("Failed to record register user audit: %s", e)
        db.rollback()

    return UserResponse.model_validate(new_user)

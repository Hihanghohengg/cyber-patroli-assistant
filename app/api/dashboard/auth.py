"""Authentication endpoints for Web Dashboard."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intelligence import DashboardUser
from app.auth.jwt_handler import verify_password, hash_password, create_access_token
from app.auth.dependencies import get_current_user, require_role, seed_default_admin_if_needed
from app.schemas.dashboard import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Dashboard Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate dashboard analyst/admin and issue JWT bearer token."""
    # Ensure default admin is created if table is empty
    seed_default_admin_if_needed(db)

    user = db.query(DashboardUser).filter(DashboardUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nama pengguna atau kata sandi tidak sesuai",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun ini telah dinonaktifkan oleh Administrator",
        )

    # Update last login time
    user.last_login_at = datetime.utcnow()
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
    username: str,
    password: str,
    full_name: str = "",
    role: str = "ANALYST",
    admin_user: DashboardUser = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to create new analyst accounts."""
    if db.query(DashboardUser).filter(DashboardUser.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama pengguna sudah terdaftar",
        )

    new_user = DashboardUser(
        username=username,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role.upper(),
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)

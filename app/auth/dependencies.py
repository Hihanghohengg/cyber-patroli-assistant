"""FastAPI dependencies for dashboard authentication and RBAC."""

from typing import Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intelligence import DashboardUser
from app.auth.jwt_handler import decode_access_token, hash_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/dashboard/auth/login", auto_error=False)


def seed_default_admin_if_needed(db: Session) -> DashboardUser:
    """Ensure at least one admin user exists on initial launch."""
    existing = db.query(DashboardUser).first()
    if not existing:
        admin = DashboardUser(
            username="admin",
            hashed_password=hash_password("patroladmin2026"),
            full_name="Petugas Patroli Siber",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    return existing


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    query_token: Optional[str] = Query(None, alias="token"),
) -> DashboardUser:
    """Authenticate request using bearer JWT token or ?token= query parameter."""
    # Ensure default admin exists
    seed_default_admin_if_needed(db)

    effective_token = token or query_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentikasi gagal atau sesi telah berakhir",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not effective_token:
        raise credentials_exception

    payload = decode_access_token(effective_token)
    if not payload:
        raise credentials_exception

    username: str = payload.get("sub")
    if not username:
        raise credentials_exception

    user = db.query(DashboardUser).filter(DashboardUser.username == username).first()
    if not user or not user.is_active:
        raise credentials_exception

    return user


def require_role(required_role: str):
    """Enforce specific role access."""
    def role_checker(current_user: DashboardUser = Depends(get_current_user)) -> DashboardUser:
        if current_user.role != required_role and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak: Memerlukan hak akses lebih tinggi",
            )
        return current_user
    return role_checker

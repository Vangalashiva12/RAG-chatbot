from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user_id
from app.core.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session


def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


def require_admin(
    user: User = Depends(get_current_user)
):
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user
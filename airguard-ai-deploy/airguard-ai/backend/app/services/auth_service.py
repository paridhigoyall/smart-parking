import uuid

from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.users.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    def issue_tokens(self, user: User) -> dict[str, str]:
        return {
            "access_token": create_access_token(str(user.id), user.role.value),
            "refresh_token": create_refresh_token(str(user.id)),
            "token_type": "bearer",
        }

    def refresh_access_token(self, refresh_token: str) -> dict[str, str] | None:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        try:
            user_id = uuid.UUID(payload.get("sub", ""))
        except ValueError:
            return None
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return None
        return self.issue_tokens(user)

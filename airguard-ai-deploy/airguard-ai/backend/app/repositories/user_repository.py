from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserSelfUpdate, UserUpdate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def list(self, skip: int = 0, limit: int = 50) -> list[User]:
        return list(self.db.scalars(select(User).offset(skip).limit(limit)))

    def create(self, payload: UserCreate) -> User:
        user = User(
            full_name=payload.full_name,
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            role=payload.role,
            phone_number=payload.phone_number,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, payload: UserUpdate | UserSelfUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        if "password" in data and data["password"]:
            user.hashed_password = hash_password(data.pop("password"))
        for field, value in data.items():
            setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

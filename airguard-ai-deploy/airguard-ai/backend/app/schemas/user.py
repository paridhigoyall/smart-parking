import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone_number: str | None = None
    role: UserRole = UserRole.EMPLOYEE


class UserCreate(UserBase):
    """Used by admins to create users with any role. Never expose this to public registration."""

    password: str = Field(min_length=8, max_length=128)


class UserSelfRegister(BaseModel):
    """Used by the public /auth/register endpoint. Deliberately excludes `role` and
    `is_superuser` so an anonymous caller cannot self-assign elevated privileges.
    New self-registered accounts always land as UserRole.EMPLOYEE and are promoted
    by an admin afterwards via PATCH /users/{user_id}."""

    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone_number: str | None = None
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    push_token: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_superuser: bool


class UserSelfUpdate(BaseModel):
    """Fields a user may change about themselves. Deliberately excludes
    `role` and `is_active` — the same self-privilege-escalation concern as
    /auth/register applies here, so those stay admin-only via UserUpdate."""
    full_name: str | None = None
    phone_number: str | None = None
    push_token: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

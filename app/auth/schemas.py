import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmailInput(Input):
    Email: str = Field(min_length=3, max_length=255)

    @field_validator("Email", mode="before")
    @classmethod
    def email(cls, value):
        if not isinstance(value, str):
            raise ValueError("Invalid email")
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
            raise ValueError("Invalid email address")
        return value


class LoginInput(EmailInput):
    Password: str = Field(min_length=1, max_length=128)

    @field_validator("Email")
    @classmethod
    def university(cls, value):
        if not value.endswith("@polytechnic.am"):
            raise ValueError("Use an @polytechnic.am student address")
        return value


class StudentLoginInput(LoginInput):
    RememberMe: bool = Field(default=False, strict=True)


class AdminLoginInput(EmailInput):
    Password: str = Field(min_length=1, max_length=128)


class RegisterInput(LoginInput):
    Password: str = Field(min_length=12, max_length=128)
    Language: Literal["hy", "en"] = "hy"


class RosterInput(EmailInput):
    FirstName: str = Field(min_length=1, max_length=100)
    LastName: str = Field(min_length=1, max_length=100)
    GroupID: int = Field(gt=0, strict=True)

    @field_validator("Email")
    @classmethod
    def university(cls, value):
        if not value.endswith("@polytechnic.am"):
            raise ValueError("Use an @polytechnic.am student address")
        return value

    @field_validator("FirstName", "LastName", mode="before")
    @classmethod
    def name(cls, value):
        return value.strip() if isinstance(value, str) else value


class StudentCreate(RosterInput):
    Password: str = Field(min_length=12, max_length=128)


class RosterState(Input):
    IsActive: bool = Field(strict=True)


class RecoveryInput(EmailInput):
    Role: Literal["student", "admin"] = "student"
    Language: Literal["hy", "en"] = "hy"


class RecoveryRequestInput(EmailInput):
    Language: Literal["hy", "en"] = "hy"


class TokenInput(Input):
    Token: str = Field(min_length=40, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class ResetInput(TokenInput):
    Password: str = Field(min_length=12, max_length=128)


class UserUpdate(Input):
    FirstName: str = Field(min_length=1, max_length=100)
    LastName: str = Field(min_length=1, max_length=100)
    Status: Literal["Active", "Suspended", "Banned"]
    GroupID: int | None = Field(default=None, gt=0, strict=True)

    @field_validator("FirstName", "LastName", mode="before")
    @classmethod
    def clean(cls, value):
        return value.strip() if isinstance(value, str) else value


class ResetCodeInput(RecoveryRequestInput):
    Code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")

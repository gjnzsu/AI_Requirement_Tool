"""Pydantic models for FastAPI auth endpoints."""

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginUser(BaseModel):
    id: int
    username: str
    email: str


class AuthUser(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[str] = None
    is_active: Optional[bool] = None


class LoginResponse(BaseModel):
    token: str
    user: LoginUser


class MeResponse(BaseModel):
    user: AuthUser


class LogoutResponse(BaseModel):
    success: bool
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: Optional[str] = None
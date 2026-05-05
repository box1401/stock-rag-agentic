from __future__ import annotations

from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from app.core.settings import get_settings


class CurrentUser(BaseModel):
    sub: str
    email: str | None = None
    role: str | None = None
    raw: dict[str, Any] = {}


def _decode(token: str) -> dict[str, Any]:
    secret = get_settings().supabase_jwt_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured: SUPABASE_JWT_SECRET missing",
        )
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
        ) from e


def _from_header(authorization: str | None) -> CurrentUser | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = _decode(token)
    return CurrentUser(
        sub=str(payload.get("sub", "")),
        email=payload.get("email"),
        role=payload.get("role"),
        raw=payload,
    )


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    user = _from_header(authorization)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return user


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
) -> CurrentUser | None:
    """Use in dev / public endpoints. Returns None instead of raising when missing."""
    if not authorization:
        return None
    try:
        return _from_header(authorization)
    except HTTPException:
        return None

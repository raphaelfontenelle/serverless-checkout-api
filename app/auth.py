"""
Authentication for the checkout service.

This module implements a small JWT-based authentication layer. It can
issue a signed token for valid credentials and verify that token on
protected endpoints. Keeping it stateless (all the information lives in
the token) fits a distributed deployment, where any instance can verify
a request without sharing session state.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# The signing secret and settings come from the environment so they are
# not hard-coded in the source. A fallback is provided only to keep the
# service runnable in local development.
JWT_SECRET = os.environ.get("JWT_SECRET", "local-development-secret-change-me")
JWT_ALGORITHM = "HS256"
TOKEN_TTL_MINUTES = 30

# Demo credentials for the MVP. In a real service these would live in a
# user store with hashed passwords; that is outside this challenge's
# scope, so a single known account is used.
DEMO_USERNAME = os.environ.get("DEMO_USERNAME", "admin")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "admin")

# HTTPBearer reads the "Authorization: Bearer <token>" header for us and
# returns the raw token string.
bearer_scheme = HTTPBearer()


def issue_token(username: str) -> str:
    """Create a signed JWT for the given username.

    The token carries the username as its subject and an expiry time, so
    it stops being valid after TOKEN_TTL_MINUTES.
    """
    expiry = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)
    claims = {"sub": username, "exp": expiry}
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def authenticate_user(username: str, password: str) -> bool:
    """Check the supplied credentials against the demo account."""
    return username == DEMO_USERNAME and password == DEMO_PASSWORD


def require_valid_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Verify the bearer token and return the username it belongs to.

    Used as a FastAPI dependency on protected endpoints. If the token is
    missing, malformed or expired, it raises a 401 so the request never
    reaches the endpoint logic.
    """
    token = credentials.credentials
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return claims["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

"""Bearer token authentication for FastAPI."""

import os
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify Bearer token.

    In production, validate against Azure AD / Entra ID or your auth provider.
    For demo purposes, we check against a simple env variable.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Token string if valid

    Raises:
        HTTPException: If token is invalid
    """
    expected_token = os.getenv("API_TOKEN", "demo-token-123")

    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
import logging

from .jwt_auth import jwt_verifier

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User information dictionary

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify JWT token
    payload = await jwt_verifier.verify_token(credentials.credentials)

    # Extract user information
    user_info = jwt_verifier.extract_user_info(payload)

    if not user_info.get('user_id'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token"
        )

    return user_info


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Optional dependency to get current user - returns None if not authenticated.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User information dictionary or None if not authenticated
    """
    if not credentials:
        return None

    try:
        payload = await jwt_verifier.verify_token(credentials.credentials)
        user_info = jwt_verifier.extract_user_info(payload)

        if user_info.get('user_id'):
            return user_info
    except HTTPException:
        # Log but don't raise - this is optional authentication
        logger.debug("Optional authentication failed, continuing without user")

    return None


def get_user_id(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Dependency to get just the user ID from authenticated user.

    Args:
        current_user: Current user information

    Returns:
        User ID string
    """
    return current_user['user_id']


def require_verified_email(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that requires the user to have a verified email.

    Args:
        current_user: Current user information

    Returns:
        User information dictionary

    Raises:
        HTTPException: If email is not verified
    """
    if not current_user.get('email_verified'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )

    return current_user
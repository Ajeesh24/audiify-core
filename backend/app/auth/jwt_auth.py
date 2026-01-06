import os
import jwt
import json
import httpx
from typing import Dict, Any
from fastapi import HTTPException, status
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CognitoJWTVerifier:
    """JWT verifier for AWS Cognito tokens."""

    def __init__(self):
        """Initialize Cognito JWT verifier."""
        self.region = os.environ.get('COGNITO_REGION', 'ap-southeast-2')
        self.user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        self.client_id = os.environ.get('COGNITO_CLIENT_ID')

        if not self.user_pool_id:
            raise ValueError("COGNITO_USER_POOL_ID environment variable not set")
        if not self.client_id:
            raise ValueError("COGNITO_CLIENT_ID environment variable not set")

        # Cognito public keys URL
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"

        # Manual async caching
        self._public_keys = None
        self._cache_timestamp = None
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
        self._lock = asyncio.Lock()

    async def get_public_keys(self) -> Dict[str, Any]:
        """Get and cache Cognito public keys for JWT verification."""
        async with self._lock:
            # Check if cache is still valid
            now = datetime.now()
            if (self._public_keys and self._cache_timestamp and
                (now - self._cache_timestamp) < self._cache_duration):
                return self._public_keys

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.jwks_url)
                    response.raise_for_status()
                    self._public_keys = response.json()
                    self._cache_timestamp = now
                    return self._public_keys
            except Exception as e:
                logger.error(f"Failed to fetch Cognito public keys: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to verify authentication"
                )

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode Cognito JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload with user information

        Raises:
            HTTPException: If token is invalid or verification fails
        """
        try:
            # Decode token header without verification to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')

            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing key ID"
                )

            # Get public keys
            jwks = await self.get_public_keys()

            # Find the correct public key
            public_key = None
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break

            if not public_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: public key not found"
                )

            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=self.client_id,  # Verify audience matches our client ID
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )

            # Additional validation
            token_use = payload.get('token_use')
            if token_use not in ['access', 'id']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication verification failed"
            )

    def extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from JWT payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            Dictionary with user information
        """
        user_info = {
            'user_id': payload.get('sub'),  # Cognito user ID (UUID)
            'username': payload.get('cognito:username', payload.get('username')),
            'email': payload.get('email'),
            'email_verified': payload.get('email_verified', False),
            'auth_time': payload.get('auth_time'),
            'token_use': payload.get('token_use'),
            'client_id': payload.get('aud'),
            'groups': payload.get('cognito:groups', []),
        }

        # Handle different token types
        if payload.get('token_use') == 'id':
            # ID token has more user profile information
            user_info.update({
                'name': payload.get('name'),
                'given_name': payload.get('given_name'),
                'family_name': payload.get('family_name'),
                'picture': payload.get('picture'),
            })

        return user_info


# Global instance
jwt_verifier = CognitoJWTVerifier()
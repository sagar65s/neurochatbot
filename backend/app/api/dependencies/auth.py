"""
FastAPI dependency that verifies the Firebase ID token sent in the
Authorization header and resolves the authenticated user's uid.

CRITICAL: this is the ONLY source of truth for "who is the current user".
Route handlers must never accept a user_id from the request body/query
and trust it directly.
"""
from fastapi import Header, HTTPException, status
from firebase_admin import auth as firebase_auth

from app.firebase.admin import verify_id_token
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
        )

    id_token = authorization.removeprefix("Bearer ").strip()
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        decoded = verify_id_token(id_token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Session revoked. Please log in again.")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except Exception:
        logger.exception("Unexpected error verifying Firebase ID token")
        raise HTTPException(status_code=401, detail="Could not verify authentication.")

    uid = decoded.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token: missing uid.")

    return uid

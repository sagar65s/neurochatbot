"""
Initializes the Firebase Admin SDK exactly once using service account
credentials from environment variables. This is what lets the backend
verify ID tokens issued by the frontend's Firebase Auth client SDK, and
read/write Firestore with elevated privileges.
"""
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_app = None


def init_firebase_admin():
    global _app
    if _app is not None:
        return _app

    settings = get_settings()

    # Private keys copied from the Firebase service account JSON often have
    # escaped newlines (\n as literal text) when stored in a .env file.
    private_key = settings.firebase_private_key.replace("\\n", "\n")

    cred = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key": private_key,
            "client_email": settings.firebase_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )

    _app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized for project=%s", settings.firebase_project_id)
    return _app


def verify_id_token(id_token: str) -> dict:
    """
    Verifies a Firebase ID token and returns its decoded claims.
    Raises firebase_admin.auth exceptions on invalid/expired tokens —
    callers (the auth dependency) translate these into HTTP 401s.
    """
    init_firebase_admin()
    return firebase_auth.verify_id_token(id_token, check_revoked=True)


def get_firestore_client():
    init_firebase_admin()
    return firestore.client()

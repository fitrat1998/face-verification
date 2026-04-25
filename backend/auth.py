import logging
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from flask import current_app
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity

logger = logging.getLogger(__name__)

JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "1"))


def hash_password(plain_password: str) -> str:
    """Hash *plain_password* with bcrypt and return the hash as a UTF-8 string."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if *plain_password* matches the stored *password_hash*."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error("Error verifying password: %s", exc)
        return False


def generate_token(student_id: int, student_code: str) -> str:
    """Create a JWT access token for the given student."""
    identity = str(student_id)
    additional_claims = {"student_code": student_code}
    expires = timedelta(hours=JWT_EXPIRY_HOURS)
    return create_access_token(
        identity=identity,
        additional_claims=additional_claims,
        expires_delta=expires,
    )


def get_current_student_id() -> int | None:
    """Return the student database ID from the active JWT, or None."""
    try:
        identity = get_jwt_identity()
        return int(identity) if identity is not None else None
    except Exception:  # pragma: no cover
        return None

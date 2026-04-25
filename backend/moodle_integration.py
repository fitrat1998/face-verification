"""Moodle OAuth2 / REST API integration helpers.

Provides utilities to:
- Exchange a Moodle OAuth2 authorisation code for tokens.
- Retrieve or create a Moodle user account.
- Synchronise a local session with Moodle.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

MOODLE_BASE_URL = os.getenv("MOODLE_BASE_URL", "")
MOODLE_CLIENT_ID = os.getenv("MOODLE_CLIENT_ID", "")
MOODLE_CLIENT_SECRET = os.getenv("MOODLE_CLIENT_SECRET", "")
MOODLE_REDIRECT_URI = os.getenv("MOODLE_REDIRECT_URI", "")
MOODLE_WSTOKEN = os.getenv("MOODLE_WSTOKEN", "")  # optional service token


def _ws_url() -> str:
    return f"{MOODLE_BASE_URL}/webservice/rest/server.php"


def exchange_code_for_token(code: str) -> dict | None:
    """Exchange an OAuth2 authorisation *code* for access / refresh tokens.

    Returns the token response dict, or None on failure.
    """
    if not MOODLE_BASE_URL:
        logger.warning("MOODLE_BASE_URL not configured.")
        return None

    token_url = f"{MOODLE_BASE_URL}/local/oauth/token.php"
    payload = {
        "client_id": MOODLE_CLIENT_ID,
        "client_secret": MOODLE_CLIENT_SECRET,
        "redirect_uri": MOODLE_REDIRECT_URI,
        "grant_type": "authorization_code",
        "code": code,
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error("Moodle token exchange failed: %s", exc)
        return None


def get_or_create_moodle_user(student_email: str, student_name: str, username: str) -> str | None:
    """Return the Moodle user ID for *student_email*, creating the user if needed.

    Requires MOODLE_WSTOKEN to be configured.
    Returns the Moodle user id string, or None on failure.
    """
    if not MOODLE_BASE_URL or not MOODLE_WSTOKEN:
        logger.warning("Moodle WS token or base URL not configured.")
        return None

    # Try to find existing user
    try:
        resp = requests.get(
            _ws_url(),
            params={
                "wstoken": MOODLE_WSTOKEN,
                "wsfunction": "core_user_get_users_by_field",
                "moodlewsrestformat": "json",
                "field": "email",
                "values[0]": student_email,
            },
            timeout=10,
        )
        resp.raise_for_status()
        users = resp.json()
        if isinstance(users, list) and users:
            return str(users[0]["id"])
    except requests.RequestException as exc:
        logger.error("Moodle user lookup failed: %s", exc)
        return None

    # Create user
    try:
        first, *rest = student_name.split(" ", 1)
        last = rest[0] if rest else first
        resp = requests.post(
            _ws_url(),
            params={
                "wstoken": MOODLE_WSTOKEN,
                "wsfunction": "core_user_create_users",
                "moodlewsrestformat": "json",
            },
            data={
                "users[0][username]": username,
                "users[0][email]": student_email,
                "users[0][firstname]": first,
                "users[0][lastname]": last,
                "users[0][auth]": "manual",
                "users[0][password]": os.urandom(16).hex(),  # random initial password
            },
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list) and result:
            return str(result[0]["id"])
    except requests.RequestException as exc:
        logger.error("Moodle user creation failed: %s", exc)

    return None


def create_moodle_session_token(moodle_user_id: str) -> dict | None:
    """Generate a Moodle login token for *moodle_user_id* via the REST API.

    Returns a dict with 'token' and 'expires_at', or None on failure.
    """
    if not MOODLE_BASE_URL or not MOODLE_WSTOKEN:
        return None

    try:
        resp = requests.post(
            _ws_url(),
            params={
                "wstoken": MOODLE_WSTOKEN,
                "wsfunction": "auth_userkey_request_login_url",
                "moodlewsrestformat": "json",
            },
            data={"user[id]": moodle_user_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        login_url = data.get("loginurl", "")
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        return {"login_url": login_url, "expires_at": expires_at}
    except requests.RequestException as exc:
        logger.error("Moodle session token creation failed: %s", exc)
        return None

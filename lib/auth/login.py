from typing import Any

import streamlit as st
import structlog

from lib.db.client import get_user_client
from lib.exceptions import UnauthorizedError
from supabase import create_client

logger = structlog.get_logger(__name__)


def sign_in(email: str, password: str) -> dict[str, Any]:
    """Authenticate user with email/password. Returns session + user dicts."""
    try:
        url: str = st.secrets["SUPABASE_URL"]
        anon_key: str = st.secrets["SUPABASE_ANON_KEY"]
        client = create_client(url, anon_key)
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        session = response.session
        user = response.user
        session_dict = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
            "token_type": session.token_type,
        }
        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "created_at": str(user.created_at),
        }
        logger.info("user_signed_in", user_id=str(user.id))
        return {"session": session_dict, "user": user_dict}
    except Exception as exc:
        err_str = str(exc).lower()
        if "invalid" in err_str or "credentials" in err_str or "auth" in err_str:
            raise UnauthorizedError("Invalid email or password") from exc
        raise UnauthorizedError(str(exc)) from exc


def sign_out(access_token: str) -> None:
    """Sign out the user. Errors are suppressed."""
    try:
        client = get_user_client(access_token)
        client.auth.sign_out()
        logger.info("user_signed_out")
    except Exception as exc:
        logger.warning("sign_out_failed", error=str(exc))


def reset_password_email(email: str, app_url: str) -> None:
    """Send a password reset email."""
    url: str = st.secrets["SUPABASE_URL"]
    anon_key: str = st.secrets["SUPABASE_ANON_KEY"]
    client = create_client(url, anon_key)
    client.auth.reset_password_email(
        email,
        options={"redirect_to": f"{app_url}/?reset=true"},
    )
    logger.info("password_reset_email_sent", email=email)


def restore_session(access_token: str, refresh_token: str) -> dict[str, Any] | None:
    """Restore a session from stored tokens. Returns session+user or None."""
    try:
        url: str = st.secrets["SUPABASE_URL"]
        anon_key: str = st.secrets["SUPABASE_ANON_KEY"]
        client = create_client(url, anon_key)
        response = client.auth.set_session(access_token, refresh_token)
        if not response.session or not response.user:
            return None
        session = response.session
        user = response.user
        return {
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
                "token_type": session.token_type,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "created_at": str(user.created_at),
            },
        }
    except Exception as exc:
        logger.warning("restore_session_failed", error=str(exc))
        return None

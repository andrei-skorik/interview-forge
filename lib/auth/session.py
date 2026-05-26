import time
from typing import Any, cast
from uuid import UUID

import streamlit as st

from lib.db.client import get_user_client


def get_current_user() -> dict[str, Any] | None:
    """Returns user dict from st.session_state or None."""
    return cast(dict[str, Any] | None, st.session_state.get("supabase_user"))


def get_current_user_id() -> UUID | None:
    user = get_current_user()
    if user and "id" in user:
        return UUID(user["id"])
    return None


def get_access_token() -> str | None:
    session = st.session_state.get("supabase_session")
    if session:
        return cast(str | None, session.get("access_token"))
    return None


def set_session(session_data: dict[str, Any], user_data: dict[str, Any]) -> None:
    st.session_state["supabase_session"] = session_data
    st.session_state["supabase_user"] = user_data


def clear_session() -> None:
    st.session_state.pop("supabase_session", None)
    st.session_state.pop("supabase_user", None)


def is_authenticated() -> bool:
    return get_current_user_id() is not None


def is_token_expired() -> bool:
    """Return True if the stored access token has expired or expires within 60 seconds."""
    session = st.session_state.get("supabase_session")
    if not session:
        return True
    expires_at = session.get("expires_at")
    if expires_at is None:
        return False
    try:
        return time.time() > float(expires_at) - 60  # 60-second buffer
    except (TypeError, ValueError):
        return False


def get_refresh_token() -> str | None:
    session = st.session_state.get("supabase_session")
    if session:
        return cast(str | None, session.get("refresh_token"))
    return None


def is_admin() -> bool:
    """Check profiles.is_admin in DB."""
    user_id = get_current_user_id()
    if not user_id:
        return False
    token = get_access_token()
    if not token:
        return False
    try:
        client = get_user_client(token)
        result = (
            client.table("profiles").select("is_admin").eq("id", str(user_id)).single().execute()
        )
        return bool(result.data and result.data.get("is_admin"))
    except Exception:
        return False

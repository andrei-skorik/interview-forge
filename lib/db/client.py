from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st
import structlog

if TYPE_CHECKING:
    from supabase import Client

logger = structlog.get_logger(__name__)


def get_user_client(access_token: str) -> Client:
    """Create a Supabase client that uses the user's JWT for RLS enforcement."""
    from supabase.lib.client_options import ClientOptions

    from supabase import create_client

    url: str = st.secrets["SUPABASE_URL"]
    anon_key: str = st.secrets["SUPABASE_ANON_KEY"]
    options = ClientOptions(headers={"Authorization": f"Bearer {access_token}"})
    return create_client(url, anon_key, options=options)


@st.cache_resource
def get_service_client() -> Client:
    """Singleton Supabase client with service role key (bypasses RLS)."""
    from supabase import create_client

    url: str = st.secrets["SUPABASE_URL"]
    service_key: str = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, service_key)

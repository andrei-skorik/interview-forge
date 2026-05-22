import re
from typing import Any

import streamlit as st
import structlog
from pydantic import BaseModel, EmailStr, field_validator

from lib.exceptions import ValidationError
from supabase import create_client

logger = structlog.get_logger(__name__)


class RegisterForm(BaseModel):
    email: EmailStr
    password: str
    gdpr_consent: bool
    marketing_consent: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least 1 uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least 1 digit")
        return v

    @field_validator("gdpr_consent")
    @classmethod
    def gdpr_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept Privacy Policy and Terms")
        return v


def register_user(form: RegisterForm, app_url: str) -> dict[str, Any]:
    """Register a new user via Supabase Auth. Returns the signup response data."""
    try:
        url: str = st.secrets["SUPABASE_URL"]
        anon_key: str = st.secrets["SUPABASE_ANON_KEY"]
        client = create_client(url, anon_key)
        response = client.auth.sign_up(
            {
                "email": form.email,
                "password": form.password,
                "options": {
                    "data": {"marketing_consent": form.marketing_consent},
                    "email_redirect_to": f"{app_url}/?confirm=true",
                },
            }
        )
        user = response.user
        logger.info(
            "user_registered",
            user_id=str(user.id) if user else None,
        )
        if user:
            return {
                "id": str(user.id),
                "email": user.email,
                "confirmation_sent": True,
            }
        return {"confirmation_sent": True}
    except Exception as exc:
        err_str = str(exc)
        if "already registered" in err_str.lower() or "already exists" in err_str.lower():
            raise ValidationError("This email is already registered") from exc
        raise ValidationError(err_str) from exc

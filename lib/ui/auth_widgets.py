from __future__ import annotations

import streamlit as st
from pydantic import ValidationError as PydanticValidationError

from lib.auth.login import reset_password_email, sign_in, sign_out
from lib.auth.register import RegisterForm, register_user
from lib.auth.session import clear_session, get_current_user, is_authenticated, set_session
from lib.exceptions import UnauthorizedError, ValidationError


def render_account_widget() -> None:
    """Render login status + sign-out or sign-up prompt in sidebar."""
    if not is_authenticated():
        st.button(
            "Sign up to save history",
            use_container_width=True,
            on_click=lambda: st.session_state.update({"app_mode": "auth"}),
        )
        if st.button("Already have an account? Sign in", use_container_width=True):
            st.session_state["app_mode"] = "auth"
            st.session_state["auth_tab"] = "login"
            st.rerun()
    else:
        user = get_current_user()
        email = user.get("email", "") if user else ""
        st.markdown(f"**{email}**")
        st.caption("Logged in")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ Settings", use_container_width=True):
                st.switch_page("pages/2_⚙️_Settings.py")
        with col2:
            if st.button("Sign out", use_container_width=True):
                from lib.auth.session import get_access_token

                token = get_access_token()
                if token:
                    sign_out(token)
                clear_session()
                st.rerun()


def login_form() -> None:
    """Render email/password sign-in form."""
    st.subheader("Sign in")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Sign in", type="primary", use_container_width=True, key="login_submit"):
        if not email or not password:
            st.error("Please enter your email and password.")
        else:
            try:
                result = sign_in(email, password)
                set_session(result["session"], result["user"])
                st.session_state["app_mode"] = "landing"
                st.rerun()
            except UnauthorizedError as e:
                st.error(e.detail or e.user_message)

    if st.button("Forgot password?", key="forgot_password"):
        st.session_state["show_reset_form"] = True

    if st.session_state.get("show_reset_form"):
        reset_email = st.text_input("Enter your email for reset link", key="reset_email")
        if st.button("Send reset link", key="send_reset"):
            try:
                app_url = st.secrets.get("APP_URL", "https://interviewforge.streamlit.app")
                reset_password_email(reset_email, app_url)
                st.success("Password reset link sent. Check your email.")
                st.session_state["show_reset_form"] = False
            except Exception:
                st.error("Could not send reset email. Please try again.")


def register_form() -> None:
    """Render registration form with GDPR consent."""
    st.subheader("Create account")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input(
        "Password",
        type="password",
        key="reg_password",
        help="Min 8 characters, 1 uppercase, 1 digit",
    )
    confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm")

    gdpr_consent = st.checkbox(
        "I agree to [Privacy Policy](/Privacy) and [Terms of Service](/Terms)",
        key="gdpr_consent",
    )
    marketing_consent = st.checkbox(
        "I'd like to receive tips and interview guides (optional)",
        key="marketing_consent",
    )

    if st.button("Create account", type="primary", use_container_width=True, key="register_submit"):
        if password != confirm_password:
            st.error("Passwords don't match.")
        elif not gdpr_consent:
            st.error(
                "You must accept the Privacy Policy and Terms of Service to create an account."
            )
        else:
            try:
                form = RegisterForm(
                    email=email,
                    password=password,
                    gdpr_consent=gdpr_consent,
                    marketing_consent=marketing_consent,
                )
                app_url = st.secrets.get("APP_URL", "https://interviewforge.streamlit.app")
                register_user(form, app_url)
                st.success(
                    "Account created! Check your email to confirm your address before signing in."
                )
            except ValidationError as e:
                st.error(e.user_message)
            except PydanticValidationError as e:
                first_err = e.errors()[0].get("msg", str(e))
                st.error(first_err)

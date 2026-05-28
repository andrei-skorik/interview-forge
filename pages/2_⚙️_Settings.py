import json
from uuid import UUID

import streamlit as st

from lib.auth.gdpr import delete_account, export_user_data
from lib.auth.login import sign_out
from lib.auth.session import (
    clear_session,
    get_access_token,
    get_current_user,
    get_current_user_id,
    is_authenticated,
)
from lib.db.client import get_user_client  # noqa: E402
from lib.exceptions import ValidationError  # noqa: E402

if not is_authenticated():
    st.warning("Please sign in to access Settings.")
    if st.button("← Go to home"):
        st.switch_page("app.py")
    st.stop()

user_id: UUID = get_current_user_id()  # type: ignore[assignment]
access_token: str = get_access_token() or ""
user = get_current_user() or {}

st.title("⚙️ Settings")

# ── Profile ────────────────────────────────────────────────────────────────────
st.subheader("Profile")
st.text_input("Email", value=user.get("email", ""), disabled=True, key="profile_email")

# Marketing consent toggle
try:
    client = get_user_client(access_token)
    profile_resp = (
        client.table("profiles").select("marketing_consent").eq("id", str(user_id)).execute()
    )
    current_marketing = (
        bool(profile_resp.data[0].get("marketing_consent")) if profile_resp.data else False
    )
except Exception:
    current_marketing = False

marketing_consent = st.toggle(
    "Receive interview tips and product updates",
    value=current_marketing,
    key="marketing_toggle",
)
if marketing_consent != current_marketing:
    try:
        client = get_user_client(access_token)
        client.table("profiles").update({"marketing_consent": marketing_consent}).eq(
            "id", str(user_id)
        ).execute()
        st.success("Preference saved.")
    except Exception:
        st.error("Could not save preference.")

st.divider()

# ── Data export ────────────────────────────────────────────────────────────────
st.subheader("Export my data")
st.caption("Download all your interview sessions, evaluations, and profile data (GDPR Art. 20).")

if st.button("📥 Prepare data export"):
    with st.spinner("Preparing export..."):
        try:
            data = export_user_data(user_id, access_token)
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(data, indent=2, default=str),
                file_name="my_interview_data.json",
                mime="application/json",
            )
        except Exception as exc:
            st.error(f"Could not export data: {exc}")

st.divider()

# ── Danger zone ────────────────────────────────────────────────────────────────
st.subheader("Danger zone")
with st.container(border=True):
    st.markdown("**Delete account**")
    st.warning(
        "This will permanently delete your account, all sessions, messages, and evaluations. "
        "This action cannot be undone."
    )
    email_confirm = st.text_input(
        "Type your email to confirm deletion",
        key="delete_confirm",
        placeholder=user.get("email", "your@email.com"),
    )
    if st.button("🗑️ Delete my account", type="primary", key="delete_account_btn"):
        try:
            delete_account(user_id, email_confirm, access_token)
            sign_out(access_token)
            clear_session()
            st.success("Your account has been permanently deleted.")
            st.switch_page("app.py")
        except ValidationError as exc:
            st.error(exc.user_message)
        except Exception as exc:
            st.error(f"Could not delete account: {exc}")

import streamlit as st

st.set_page_config(page_title="Privacy Policy", page_icon="🔒", layout="centered")

try:
    admin_email: str = st.secrets.get("ADMIN_EMAIL", "privacy@interviewforge.app")
except Exception:
    admin_email = "privacy@interviewforge.app"

st.title("🔒 Privacy Policy")
st.caption("Last updated: 2026-05-21")

st.markdown(f"""
## 1. Data Controller

InterviewForge is operated by its author ("we", "us"). For privacy-related inquiries, contact
us at **{admin_email}**. We respond to all requests within 30 days as required by GDPR Art. 12.

---

## 2. What We Collect

| Data | Purpose | Legal basis |
|------|---------|-------------|
| Email address | Account creation and login | Consent (Art. 6(1)(a)) |
| Interview sessions (job descriptions, answers) | Providing the practice service | Contract (Art. 6(1)(b)) |
| Evaluation scores and reports | Showing you your performance history | Contract (Art. 6(1)(b)) |
| Marketing consent flag | Sending optional tips (only if you opt in) | Consent (Art. 6(1)(a)) |
| Anonymised audit logs (SHA-256 hashed user IDs) | Security and compliance | Legitimate interest (Art. 6(1)(f)) |

We do **not** collect: your real name, phone number, location data, or any information beyond
what is listed above.

---

## 3. How We Use Your Data

- To run your mock interviews and generate AI feedback
- To display your session history on the Dashboard
- To send you optional tips about interview preparation (only if `marketing_consent = true`)
- To detect and prevent abuse (prompt injection, rate-limit violations)

We do **not** use your data for advertising, profiling, or sale to third parties.

---

## 4. Third-Party Processors

| Processor | Role | Region | DPA |
|-----------|------|--------|-----|
| **Supabase** | Database and authentication | EU (Frankfurt, eu-central-1) | Automatic (EU region) |
| **OpenRouter** | LLM API gateway (interview questions, evaluation) | See their privacy policy | Standard Contractual Clauses |
| **Streamlit Community Cloud** | App hosting | EU region selected at creation | See Snowflake DPA |
| **European Central Bank** | Currency conversion rates (no personal data sent) | EU | N/A |

---

## 5. Data Retention

- **Authenticated accounts:** data retained until you delete your account.
- **Guest sessions:** automatically deleted after 7 days (via `guest_token_expires_at`).
- **Backups:** Supabase point-in-time recovery, retained per Supabase policy.

---

## 6. Your Rights (GDPR)

You have the following rights under GDPR:

- **Access (Art. 15):** View your profile on the Settings page.
- **Rectification (Art. 16):** Update your profile on the Settings page.
- **Erasure (Art. 17):** Delete your account in Settings → "Delete my account".
- **Portability (Art. 20):** Download all your data as JSON in Settings → "Export my data".
- **Restriction (Art. 18) / Objection (Art. 21):** Email us at **{admin_email}**.
- **Withdraw consent (Art. 7):** Toggle "marketing_consent" off in Settings at any time.

---

## 7. Cookie Policy

We use **only functional cookies** (Streamlit session cookies) required for the app to work.
We do **not** use advertising or analytics cookies. No third-party trackers are embedded.

---

## 8. Contact and Complaints

For any privacy questions: **{admin_email}**

If you believe your rights have been violated, you may lodge a complaint with the supervisory
authority in your EU member state. For Berlin-based residents:

**Berliner Beauftragte für Datenschutz und Informationsfreiheit**
www.datenschutz-berlin.de
""")

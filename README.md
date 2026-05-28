# InterviewForge — Launch Guide

An AI-powered mock interview trainer for the EU IT job market. Built with Streamlit, it provides multi-turn interview sessions, LLM-based evaluation, and structured performance reports.

---

## Prerequisites

| Requirement | Version | Where to get |
|-------------|---------|--------------|
| Python | 3.12+ (tested on 3.14.5) | python.org |
| Supabase project | eu-central-1 (Frankfurt) | supabase.com |
| OpenRouter API key | — | openrouter.ai |
| Supabase CLI | latest | supabase.com/docs/guides/cli |

---

## Step 1: Install dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install app dependencies
pip install -r requirements.txt

# Install dev dependencies (tests, linter, mypy)
pip install -r requirements-dev.txt
```

---

## Step 2: Configure secrets

```powershell
# Copy the secrets template
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Open `.streamlit\secrets.toml` and fill in all values:

```toml
SUPABASE_URL = "https://[your-project-ref].supabase.co"
SUPABASE_ANON_KEY = "eyJ..."          # Supabase → Settings → API → anon key
SUPABASE_SERVICE_ROLE_KEY = "eyJ..."  # Supabase → Settings → API → service_role key
OPENROUTER_API_KEY = "sk-or-v1-..."   # openrouter.ai → Keys
APP_URL = "http://localhost:8501"      # for local development
ADMIN_EMAIL = "your@email.com"
DEV_MODE = true                        # enable only for local development
```

> **IMPORTANT:** `.streamlit/secrets.toml` is listed in `.gitignore`. Never commit it to git.

---

## Step 3: Apply database migrations

```powershell
# Log in to Supabase CLI
supabase login

# Link to your project
supabase link --project-ref [your-project-ref]

# Apply all migrations (001–006)
supabase db push
```

Migrations are applied in order:
1. `001_initial_schema.sql` — profiles, base types
2. `002_sessions_messages.sql` — sessions and messages
3. `003_pgvector_setup.sql` — vector extension, embeddings
4. `004_evaluations_reports.sql` — evaluations and reports
5. `005_security_audit.sql` — security_events, audit_log
6. `006_rls_policies.sql` — 22 Row-Level Security policies

> After applying, all tables should appear in the Supabase Dashboard with RLS enabled.

---

## Step 4: Run the application

```powershell
# Make sure the venv is activated
.\venv\Scripts\Activate.ps1

# Start the app
streamlit run app.py
```

The app will open at: **http://localhost:8501**

### Pages

| URL | Page | Access |
|-----|------|--------|
| `/` | Home (chat interview) | Everyone |
| `/Dashboard` | Session history and stats | Authenticated |
| `/Settings` | Profile, GDPR export/delete | Authenticated |
| `/Admin` | Management, metrics, pricing | Admin only |
| `/Privacy` | Privacy policy | Everyone |
| `/Terms` | Terms of service | Everyone |
| `/Report` | Detailed session report | Authenticated |

---

## Step 5: Seed initial data (optional, for Admin panel)

For model pricing to display correctly in the Admin panel, run these scripts once manually:

```powershell
# Fetch USD → EUR exchange rate from ECB
python scripts\refresh_currency.py

# Fetch model pricing from OpenRouter
python scripts\refresh_pricing.py
```

After initial setup these run automatically via GitHub Actions.

---

## Running tests

```powershell
# All unit tests (excluding tests that require a live Supabase connection)
pytest tests/ `
  --ignore=tests/test_integration `
  --ignore=tests/test_db/test_rls_isolation.py `
  --ignore=tests/test_db/test_cascade_delete.py `
  --ignore=tests/test_db/test_pgvector_search.py `
  -v

# Security tests only (injection guards)
pytest -k test_injection -v

# Judge tests only
pytest tests/test_judge/ -v
```

### Test suite overview

| Suite | Tests | Requires Supabase |
|-------|-------|-------------------|
| test_prompts | ~40 | No |
| test_security | ~20 | No |
| test_judge | ~30 | No |
| test_db (unit) | ~30 | No |
| test_integration | ~10 | Yes |
| test_db/test_rls_* | ~30 | Yes |

---

## Code quality checks

```powershell
# Linting
ruff check .

# Format check (no changes applied)
ruff format --check .

# Apply formatting
ruff format .

# Type checking (strict mode)
mypy .
```

All three commands must pass with zero errors before committing.

---

## Deploying to Streamlit Community Cloud

1. Push the code to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select the repository, branch `main`, file `app.py`
4. Choose region **EU (Frankfurt)**
5. In **Advanced settings → Secrets**, paste the contents of your `secrets.toml` (with real values)
6. Click **Deploy**

After deployment update `APP_URL` in secrets to the actual URL: `https://[your-app].streamlit.app`.

---

## GitHub Actions (automated tasks)

### CI (`ci.yml`)
Runs on every push and pull request:
- `ruff check .`
- `mypy .`
- `pytest` (unit tests)

### Scheduled jobs (`scheduled.yml`)

| Job | Schedule | Script |
|-----|----------|--------|
| Refresh EUR/USD rate | Daily at 08:00 UTC | `scripts/refresh_currency.py` |
| Refresh model pricing | Every hour | `scripts/refresh_pricing.py` |
| Clean up guest sessions | Daily at 02:00 UTC | `scripts/cleanup_guests.py` |
| Clean up abandoned sessions | Daily at 03:00 UTC | `scripts/cleanup_abandoned.py` |

Add these secrets to your GitHub repository (**Settings → Secrets and variables → Actions**) for scheduled jobs to work:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENROUTER_API_KEY`

---

## Project structure

```
interview-forge/
├── app.py                        # Streamlit entry point (landing + chat)
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_⚙️_Settings.py
│   ├── 3_🔒_Admin.py
│   ├── 4_📄_Privacy.py
│   ├── 5_📋_Terms.py
│   └── 6_📈_Report.py
├── lib/
│   ├── openrouter/               # HTTP client, chat, embeddings, models, cost calculator
│   ├── prompts/                  # Interviewer (5 techniques), judge, security, jd_analyzer
│   ├── db/                       # Supabase: sessions, messages, evaluations, embeddings, ...
│   ├── auth/                     # Supabase Auth + GDPR (export, delete)
│   ├── schemas/                  # Pydantic models (session, judge, jd_analysis, ...)
│   ├── ui/                       # Streamlit components (chat, sidebar, report)
│   └── utils/                    # token_counter, rate_limit, ip_hash
├── supabase/migrations/          # 6 SQL migrations (001–006)
├── scripts/                      # Standalone scripts for cron jobs
├── tests/                        # pytest suite
├── .github/workflows/            # ci.yml + scheduled.yml
├── .streamlit/
│   ├── config.toml               # Theme and server settings
│   └── secrets.toml.example      # Secrets template (secrets.toml is gitignored)
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml                # mypy strict + ruff config + pytest config
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'tiktoken'`**
```powershell
pip install tiktoken --only-binary=:all:
```

**`streamlit: command not found`**
```powershell
.\venv\Scripts\Activate.ps1
```

**`Auth session missing` on login**
Verify that `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `secrets.toml` are correct.

**RLS policy violation errors**
Check that all 6 migrations have been applied (`supabase db push`) and RLS is enabled on all tables.

**Admin panel shows no pricing data**
Run `python scripts\refresh_pricing.py` manually once — it populates the `model_pricing_cache` table in Supabase.

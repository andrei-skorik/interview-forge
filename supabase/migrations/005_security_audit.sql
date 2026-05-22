-- InterviewForge Migration 005: security_events + audit_log + model_pricing_cache + currency_rates

-- ============================================================
-- TABLE: security_events (prompt injection logs, rate limits)
-- Uses ON DELETE SET NULL to preserve logs even after user deletion (GDPR: audit trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS security_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
  ip_hash TEXT,  -- SHA-256 of IP, never raw IP (GDPR)
  event_type TEXT NOT NULL CHECK (event_type IN (
    'prompt_injection_blocked',
    'rate_limit_exceeded',
    'suspicious_input_flagged',
    'invalid_token',
    'jailbreak_attempt'
  )),
  severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  input_excerpt TEXT,  -- first 500 chars of offending input
  detection_method TEXT NOT NULL,
  detection_confidence NUMERIC(3,2),
  detection_reason TEXT,
  blocked BOOLEAN NOT NULL DEFAULT TRUE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_events_user ON security_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(ip_hash, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type, severity);

-- ============================================================
-- RLS: security_events (admin only)
-- INSERT is done via service_role client — bypasses RLS intentionally
-- ============================================================
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "security_events_admin_only" ON security_events;
CREATE POLICY "security_events_admin_only"
  ON security_events FOR SELECT
  USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = TRUE));

-- ============================================================
-- TABLE: model_pricing_cache (refreshed hourly by GitHub Actions)
-- ============================================================
CREATE TABLE IF NOT EXISTS model_pricing_cache (
  model_id TEXT PRIMARY KEY,
  prompt_price_per_million_usd NUMERIC(10,4) NOT NULL,
  completion_price_per_million_usd NUMERIC(10,4) NOT NULL,
  context_length INTEGER NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  raw_response JSONB NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE model_pricing_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pricing_select_all" ON model_pricing_cache;
CREATE POLICY "pricing_select_all"
  ON model_pricing_cache FOR SELECT
  USING (TRUE);

-- ============================================================
-- TABLE: currency_rates (USD→EUR, refreshed daily from ECB)
-- ============================================================
CREATE TABLE IF NOT EXISTS currency_rates (
  base TEXT NOT NULL,
  target TEXT NOT NULL,
  rate NUMERIC(10,6) NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (base, target, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_currency_rates_latest ON currency_rates(base, target, fetched_at DESC);

ALTER TABLE currency_rates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "currency_select_all" ON currency_rates;
CREATE POLICY "currency_select_all"
  ON currency_rates FOR SELECT
  USING (TRUE);

-- ============================================================
-- TABLE: audit_log (GDPR-anonymized actions, no PII)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymized_user_id TEXT NOT NULL,  -- SHA-256(user_id), never raw UUID
  action TEXT NOT NULL CHECK (action IN (
    'account_created',
    'account_deleted',
    'gdpr_export_requested',
    'gdpr_consent_updated',
    'session_deleted',
    'all_sessions_exported'
  )),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action, created_at DESC);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "audit_admin_only" ON audit_log;
CREATE POLICY "audit_admin_only"
  ON audit_log FOR SELECT
  USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = TRUE));

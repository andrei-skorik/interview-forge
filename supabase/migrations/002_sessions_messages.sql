-- InterviewForge Migration 002: sessions + messages tables
CREATE EXTENSION IF NOT EXISTS moddatetime;

-- ============================================================
-- TABLE: sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  guest_token TEXT UNIQUE,
  guest_token_expires_at TIMESTAMPTZ,

  job_description TEXT NOT NULL CHECK (length(job_description) BETWEEN 50 AND 10000),
  jd_analysis JSONB NOT NULL DEFAULT '{}',

  domain TEXT NOT NULL CHECK (domain IN ('frontend', 'backend', 'data_ml', 'devops', 'system_design', 'behavioral')),
  difficulty TEXT NOT NULL DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
  response_length TEXT NOT NULL DEFAULT 'detailed' CHECK (response_length IN ('concise', 'detailed')),
  interviewer_persona TEXT NOT NULL DEFAULT 'neutral' CHECK (interviewer_persona IN ('strict', 'neutral', 'friendly')),
  prompt_technique TEXT NOT NULL DEFAULT 'role_playing' CHECK (prompt_technique IN ('zero_shot', 'few_shot', 'chain_of_thought', 'role_playing', 'structured_output')),

  llm_model TEXT NOT NULL DEFAULT 'openai/gpt-5-mini' CHECK (llm_model IN ('openai/gpt-5-mini', 'openai/gpt-5-nano')),
  temperature NUMERIC(3,2) NOT NULL DEFAULT 0.70 CHECK (temperature >= 0.0 AND temperature <= 1.5),
  top_p NUMERIC(3,2) NOT NULL DEFAULT 1.00 CHECK (top_p >= 0.0 AND top_p <= 1.0),
  max_tokens INTEGER NOT NULL DEFAULT 1024 CHECK (max_tokens BETWEEN 256 AND 4096),
  frequency_penalty NUMERIC(3,2) NOT NULL DEFAULT 0.00 CHECK (frequency_penalty BETWEEN -2.0 AND 2.0),
  presence_penalty NUMERIC(3,2) NOT NULL DEFAULT 0.00 CHECK (presence_penalty BETWEEN -2.0 AND 2.0),

  status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'evaluating', 'completed', 'completed_without_eval', 'abandoned')),
  total_input_tokens INTEGER NOT NULL DEFAULT 0,
  total_output_tokens INTEGER NOT NULL DEFAULT 0,
  total_cost_usd_cents INTEGER NOT NULL DEFAULT 0,

  share_token TEXT UNIQUE,
  share_enabled BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_guest_token ON sessions(guest_token) WHERE guest_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_share_token ON sessions(share_token) WHERE share_token IS NOT NULL AND share_enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_jd_search ON sessions USING gin(to_tsvector('english', job_description));

CREATE OR REPLACE TRIGGER sessions_updated_at
  BEFORE UPDATE ON sessions
  FOR EACH ROW
  EXECUTE FUNCTION moddatetime(updated_at);

-- ============================================================
-- RLS: sessions (6 policies)
-- ============================================================
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "sessions_select_own_user" ON sessions;
CREATE POLICY "sessions_select_own_user"
  ON sessions FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "sessions_select_shared" ON sessions;
CREATE POLICY "sessions_select_shared"
  ON sessions FOR SELECT
  USING (share_enabled = TRUE AND share_token IS NOT NULL);

DROP POLICY IF EXISTS "sessions_select_admin" ON sessions;
CREATE POLICY "sessions_select_admin"
  ON sessions FOR SELECT
  USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = TRUE));

DROP POLICY IF EXISTS "sessions_insert_authenticated" ON sessions;
CREATE POLICY "sessions_insert_authenticated"
  ON sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "sessions_update_own" ON sessions;
CREATE POLICY "sessions_update_own"
  ON sessions FOR UPDATE
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "sessions_delete_own" ON sessions;
CREATE POLICY "sessions_delete_own"
  ON sessions FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================================
-- TABLE: messages
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 50000),
  sequence_number INTEGER NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cost_usd_cents INTEGER,
  latency_ms INTEGER,
  suspicious BOOLEAN NOT NULL DEFAULT FALSE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE(session_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_seq ON messages(session_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_messages_suspicious ON messages(suspicious) WHERE suspicious = TRUE;

-- ============================================================
-- RLS: messages (3 policies)
-- ============================================================
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "messages_select_via_session" ON messages;
CREATE POLICY "messages_select_via_session"
  ON messages FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = messages.session_id
      AND (
        s.user_id = auth.uid()
        OR (s.share_enabled = TRUE AND s.share_token IS NOT NULL)
        OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = TRUE)
      )
    )
  );

DROP POLICY IF EXISTS "messages_insert_via_session" ON messages;
CREATE POLICY "messages_insert_via_session"
  ON messages FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = messages.session_id
      AND s.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "messages_delete_via_session" ON messages;
CREATE POLICY "messages_delete_via_session"
  ON messages FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = messages.session_id
      AND s.user_id = auth.uid()
    )
  );

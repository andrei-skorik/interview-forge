-- InterviewForge Migration 004: evaluations + session_reports

-- ============================================================
-- TABLE: evaluations (one row per user answer in a session)
-- ============================================================
CREATE TABLE IF NOT EXISTS evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  question_message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  answer_message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,

  correctness_score INTEGER NOT NULL CHECK (correctness_score BETWEEN 1 AND 10),
  depth_score INTEGER NOT NULL CHECK (depth_score BETWEEN 1 AND 10),
  structure_score INTEGER NOT NULL CHECK (structure_score BETWEEN 1 AND 10),
  communication_score INTEGER NOT NULL CHECK (communication_score BETWEEN 1 AND 10),

  -- Computed column: average of 4 criteria
  average_score NUMERIC(3,1) GENERATED ALWAYS AS (
    (correctness_score + depth_score + structure_score + communication_score)::NUMERIC / 4
  ) STORED,

  correctness_reasoning TEXT NOT NULL,
  depth_reasoning TEXT NOT NULL,
  structure_reasoning TEXT NOT NULL,
  communication_reasoning TEXT NOT NULL,

  cost_usd_cents INTEGER NOT NULL DEFAULT 0,
  judge_model TEXT NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE(answer_message_id)
);

CREATE INDEX IF NOT EXISTS idx_evaluations_session ON evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_average ON evaluations(session_id, average_score DESC);

-- ============================================================
-- RLS: evaluations (1 policy)
-- ============================================================
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "evaluations_select_via_session" ON evaluations;
CREATE POLICY "evaluations_select_via_session"
  ON evaluations FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = evaluations.session_id
      AND (
        s.user_id = auth.uid()
        OR (s.share_enabled = TRUE AND s.share_token IS NOT NULL)
        OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = TRUE)
      )
    )
  );

-- ============================================================
-- TABLE: session_reports (final judge output, both JSON formats)
-- ============================================================
CREATE TABLE IF NOT EXISTS session_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,

  overall_score NUMERIC(3,1) NOT NULL CHECK (overall_score BETWEEN 1.0 AND 10.0),
  readiness_level TEXT NOT NULL CHECK (readiness_level IN ('not_ready', 'needs_practice', 'ready', 'strong_candidate')),

  strengths JSONB NOT NULL,
  weaknesses JSONB NOT NULL,
  improvement_plan JSONB NOT NULL,

  -- Two JSON formats — core requirement of the assignment
  summary_json JSONB NOT NULL,
  detailed_json JSONB NOT NULL,

  cost_usd_cents INTEGER NOT NULL DEFAULT 0,
  judge_model TEXT NOT NULL,
  generation_time_ms INTEGER NOT NULL,
  degraded_evaluation BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_reports_session ON session_reports(session_id);

-- ============================================================
-- RLS: session_reports (1 policy)
-- ============================================================
ALTER TABLE session_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "reports_select_via_session" ON session_reports;
CREATE POLICY "reports_select_via_session"
  ON session_reports FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sessions s
      WHERE s.id = session_reports.session_id
      AND (
        s.user_id = auth.uid()
        OR (s.share_enabled = TRUE AND s.share_token IS NOT NULL)
        OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = TRUE)
      )
    )
  );

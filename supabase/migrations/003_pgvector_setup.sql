-- InterviewForge Migration 003: pgvector extension + question_embeddings + find_similar_questions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS moddatetime;

-- ============================================================
-- TABLE: question_embeddings (pgvector 4096 dim)
-- ============================================================
CREATE TABLE IF NOT EXISTS question_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  question_text TEXT NOT NULL,
  embedding vector(4096) NOT NULL,
  domain TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE(message_id)
);

-- Note: pgvector index types (ivfflat/hnsw) support max 2000 dimensions.
-- qwen3-embedding-8b uses 4096 dims, so we skip the ANN index.
-- Similarity search falls back to sequential scan (fine for MVP scale).

CREATE INDEX IF NOT EXISTS idx_question_embeddings_user ON question_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_question_embeddings_domain ON question_embeddings(user_id, domain);

-- ============================================================
-- RLS: question_embeddings (3 policies)
-- ============================================================
ALTER TABLE question_embeddings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "embeddings_select_own" ON question_embeddings;
CREATE POLICY "embeddings_select_own"
  ON question_embeddings FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "embeddings_insert_own" ON question_embeddings;
CREATE POLICY "embeddings_insert_own"
  ON question_embeddings FOR INSERT
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "embeddings_delete_own" ON question_embeddings;
CREATE POLICY "embeddings_delete_own"
  ON question_embeddings FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================================
-- FUNCTION: find_similar_questions
-- Called from Python via supabase.rpc('find_similar_questions', {...})
-- ============================================================
CREATE OR REPLACE FUNCTION find_similar_questions(
  query_embedding vector(4096),
  target_user_id UUID,
  target_domain TEXT,
  similarity_threshold FLOAT DEFAULT 0.92,
  max_results INTEGER DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  question_text TEXT,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    qe.id,
    qe.question_text,
    1 - (qe.embedding <=> query_embedding) AS similarity
  FROM question_embeddings qe
  WHERE qe.user_id = target_user_id
    AND qe.domain = target_domain
    AND (1 - (qe.embedding <=> query_embedding)) >= similarity_threshold
  ORDER BY qe.embedding <=> query_embedding
  LIMIT max_results;
$$;

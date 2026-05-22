-- Migration 010: Add get_scores_by_technique RPC function.
-- Used by Admin Dashboard to show average score per prompt technique for a user.

CREATE OR REPLACE FUNCTION public.get_scores_by_technique(target_user_id UUID)
RETURNS TABLE (prompt_technique TEXT, avg_score NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT s.prompt_technique, AVG(e.average_score)::NUMERIC(3,1) AS avg_score
  FROM sessions s
  JOIN evaluations e ON e.session_id = s.id
  WHERE s.user_id = target_user_id
    AND s.prompt_technique IS NOT NULL
  GROUP BY s.prompt_technique;
$$;

GRANT EXECUTE ON FUNCTION public.get_scores_by_technique(UUID) TO authenticated, service_role;

-- Migration 009: Grant table permissions to Supabase roles.
-- authenticated: users with JWT (RLS enforced)
-- anon: unauthenticated users (RLS enforced)
-- service_role: server-side operations (bypasses RLS)

GRANT ALL ON public.profiles TO authenticated, service_role;
GRANT ALL ON public.sessions TO authenticated, service_role;
GRANT ALL ON public.messages TO authenticated, service_role;
GRANT ALL ON public.question_embeddings TO authenticated, service_role;
GRANT ALL ON public.evaluations TO authenticated, service_role;
GRANT ALL ON public.session_reports TO authenticated, service_role;
GRANT ALL ON public.security_events TO service_role;
GRANT ALL ON public.audit_log TO service_role;
GRANT SELECT ON public.model_pricing_cache TO authenticated, anon, service_role;
GRANT ALL ON public.model_pricing_cache TO service_role;
GRANT SELECT ON public.currency_rates TO authenticated, anon, service_role;
GRANT ALL ON public.currency_rates TO service_role;

-- Grant execute on RPC functions
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO service_role;
GRANT EXECUTE ON FUNCTION public.check_is_admin() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.find_similar_questions(vector, uuid, text, float, integer) TO authenticated, service_role;

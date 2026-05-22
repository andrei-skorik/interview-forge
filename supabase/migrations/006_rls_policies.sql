-- InterviewForge Migration 006: RLS policies reference + verification
-- All 22 policies are created inline in migrations 001-005.
-- This file documents them all and provides a verification query.

-- ============================================================
-- RLS POLICY MAP (22 policies across 10 tables)
-- ============================================================

-- TABLE: profiles (4 policies) — see 001_initial_schema.sql
--   1. profiles_select_own        SELECT USING (auth.uid() = id)
--   2. profiles_select_admin      SELECT USING (is_admin check)
--   3. profiles_update_own        UPDATE USING (auth.uid() = id)
--   4. profiles_delete_own        DELETE USING (auth.uid() = id)

-- TABLE: sessions (6 policies) — see 002_sessions_messages.sql
--   5. sessions_select_own_user   SELECT USING (auth.uid() = user_id)
--   6. sessions_select_shared     SELECT USING (share_enabled = TRUE)
--   7. sessions_select_admin      SELECT USING (is_admin check)
--   8. sessions_insert_authenticated INSERT WITH CHECK (auth.uid() = user_id)
--   9. sessions_update_own        UPDATE USING (auth.uid() = user_id)
--  10. sessions_delete_own        DELETE USING (auth.uid() = user_id)

-- TABLE: messages (3 policies) — see 002_sessions_messages.sql
--  11. messages_select_via_session SELECT via sessions join
--  12. messages_insert_via_session INSERT via sessions join
--  13. messages_delete_via_session DELETE via sessions join

-- TABLE: question_embeddings (3 policies) — see 003_pgvector_setup.sql
--  14. embeddings_select_own      SELECT USING (auth.uid() = user_id)
--  15. embeddings_insert_own      INSERT WITH CHECK (auth.uid() = user_id)
--  16. embeddings_delete_own      DELETE USING (auth.uid() = user_id)

-- TABLE: evaluations (1 policy) — see 004_evaluations_reports.sql
--  17. evaluations_select_via_session  SELECT via sessions join

-- TABLE: session_reports (1 policy) — see 004_evaluations_reports.sql
--  18. reports_select_via_session  SELECT via sessions join

-- TABLE: security_events (1 policy) — see 005_security_audit.sql
--  19. security_events_admin_only  SELECT USING (is_admin check)

-- TABLE: model_pricing_cache (1 policy) — see 005_security_audit.sql
--  20. pricing_select_all          SELECT USING (TRUE)

-- TABLE: currency_rates (1 policy) — see 005_security_audit.sql
--  21. currency_select_all         SELECT USING (TRUE)

-- TABLE: audit_log (1 policy) — see 005_security_audit.sql
--  22. audit_admin_only            SELECT USING (is_admin check)

-- Total: 22 policies | All 10 tables have RLS enabled

-- ============================================================
-- VERIFICATION QUERY (run in Supabase SQL editor to confirm)
-- Expected: 22 rows, each policy listed once
-- ============================================================
-- SELECT schemaname, tablename, policyname, cmd
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;

-- ============================================================
-- GUEST SESSION OPERATIONS NOTE
-- Guest sessions (user_id IS NULL) bypass RLS via service_role client.
-- Python code in lib/db/client.py uses SUPABASE_SERVICE_ROLE_KEY for:
--   - Guest session CREATE
--   - Guest session READ (with guest_token verification in Python)
--   - security_events INSERT
--   - account deletion cascade
-- All other operations use user-JWT client (RLS applies automatically).
-- ============================================================

-- Migration 008: Fix infinite recursion in profiles RLS policy.
-- profiles_select_admin queried profiles inside a profiles SELECT policy → recursion.
-- Fix: use a SECURITY DEFINER function which bypasses RLS, breaking the cycle.

CREATE OR REPLACE FUNCTION public.check_is_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (SELECT is_admin FROM profiles WHERE id = auth.uid()),
    false
  );
$$;

DROP POLICY IF EXISTS "profiles_select_admin" ON profiles;
CREATE POLICY "profiles_select_admin"
  ON profiles FOR SELECT
  USING (public.check_is_admin());

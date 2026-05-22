-- Migration 007: Fix handle_new_user trigger function
-- SECURITY DEFINER functions require explicit search_path to find public schema tables.
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, gdpr_consent_at, marketing_consent)
  VALUES (
    NEW.id,
    NEW.email,
    NOW(),
    COALESCE((NEW.raw_user_meta_data->>'marketing_consent')::BOOLEAN, FALSE)
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

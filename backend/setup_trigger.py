import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import text
from app.core.database import SessionLocal

def setup_trigger():
    db = SessionLocal()
    try:
        print("Creating Supabase auth.users -> public.civilians database trigger...")
        
        # 1. Create function
        db.execute(text("""
            CREATE OR REPLACE FUNCTION public.handle_new_user()
            RETURNS TRIGGER AS $$
            BEGIN
              INSERT INTO public.civilians (email, full_name, auth_provider, is_active, created_at)
              VALUES (
                NEW.email,
                COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
                'google',
                TRUE,
                NOW()
              )
              ON CONFLICT (email) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                auth_provider = EXCLUDED.auth_provider;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """))
        
        # 2. Create trigger
        db.execute(text("""
            DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
            CREATE TRIGGER on_auth_user_created
              AFTER INSERT OR UPDATE ON auth.users
              FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """))
        
        # 3. Sync all existing users from auth.users to public.civilians
        result = db.execute(text("""
            INSERT INTO public.civilians (email, full_name, auth_provider, is_active)
            SELECT 
              email,
              COALESCE(raw_user_meta_data->>'full_name', raw_user_meta_data->>'name', split_part(email, '@', 1)),
              'google',
              TRUE
            FROM auth.users
            ON CONFLICT (email) DO UPDATE SET
              full_name = EXCLUDED.full_name,
              auth_provider = EXCLUDED.auth_provider;
        """))
        
        db.commit()
        print("SUCCESS! Trigger created and existing Google users synced into public.civilians table.")
    except Exception as e:
        db.rollback()
        print("Error setting up trigger:", e)
    finally:
        db.close()

if __name__ == "__main__":
    setup_trigger()

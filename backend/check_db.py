from app.core.database import SessionLocal
from app.db.models import Civilian, TrafficController

def check_db():
    db = SessionLocal()
    try:
        civilians = db.query(Civilian).all()
        controllers = db.query(TrafficController).all()
        
        print("=== SUPABASE POSTGRESQL DATABASE CONTENTS ===")
        print(f"Total Civilians ({len(civilians)}):")
        for c in civilians:
            print(f" - ID: {c.id} | Email: {c.email} | Name: {c.full_name} | Provider: {c.auth_provider}")
            
        print(f"\nTotal Traffic Controllers ({len(controllers)}):")
        for t in controllers:
            print(f" - ID: {t.id} | Email: {t.email} | Name: {t.full_name} | Badge: {t.badge_number}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()

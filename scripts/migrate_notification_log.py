
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from sqlalchemy import text

def migrate():
    print("Migrating notifications_log table...")
    db = SessionLocal()
    try:
        # Check if column exists
        check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='notifications_log' AND column_name='notification_type'")
        result = db.execute(check_sql).fetchone()
        
        if result:
            print("Column 'notification_type' already exists.")
            return

        # Add column
        print("Adding 'notification_type' column...")
        alter_sql = text("ALTER TABLE notifications_log ADD COLUMN notification_type VARCHAR(50) DEFAULT 'vendor'")
        db.execute(alter_sql)
        db.commit()
        print("Migration successful: Added 'notification_type' column.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

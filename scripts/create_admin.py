from app.core.database import SessionLocal
from app.models.user import User
from app.models.db import SwingSession  # Import to resolve relationship
from app.core.security import get_password_hash

def create_admin():
    db = SessionLocal()
    try:
        email = "admin@example.com"
        password = "admin"
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            if not user.is_admin:
                user.is_admin = True
                db.commit()
                print(f"Updated {email} to be an admin.")
            return

        # Create new admin user
        new_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Admin User",
            is_admin=True,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"Created admin user: {email} / {password}")
        
    except Exception as e:
        print(f"Error creating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

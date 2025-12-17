"""
Quick helper to reset a user's password in the local SQLite database.

Usage:
    python scripts/reset_password.py --email user@example.com --password newpass

If you omit --password, you will be prompted (so you don't have to pass it on the CLI).
"""

import argparse
import getpass

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
# Import relationships to avoid mapper resolution issues
from app.models.db import SwingSession  # noqa: F401


def reset_password(email: str, password: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found")
            return False

        user.hashed_password = get_password_hash(password)
        db.add(user)
        db.commit()
        print(f"Updated password for {email}")
        return True
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Reset a user's password")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument(
        "--password",
        help="New password (if omitted, you will be prompted without echo)",
    )
    args = parser.parse_args()

    password = args.password or getpass.getpass("New password: ")
    reset_password(args.email.strip().lower(), password)


if __name__ == "__main__":
    main()

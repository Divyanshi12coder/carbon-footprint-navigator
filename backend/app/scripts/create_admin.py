"""Create or promote an administrator: `python -m app.scripts.create_admin --email a@b.com`.

The password is read from the ADMIN_PASSWORD environment variable or prompted for, never
passed on the command line (where it would land in shell history).
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserPreference
from app.schemas.auth import password_strength


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    email = args.email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role = "admin"
            db.commit()
            print(f"Promoted existing user {email} to admin.")
            return
        password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
        try:
            password_strength(password)
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters.")
        except ValueError as exc:
            sys.exit(str(exc))
        db.add(
            User(
                email=email,
                full_name=args.name,
                hashed_password=hash_password(password),
                role="admin",
                onboarding_completed=True,
                preferences=UserPreference(),
            )
        )
        db.commit()
        print(f"Created admin {email}.")


if __name__ == "__main__":
    main()

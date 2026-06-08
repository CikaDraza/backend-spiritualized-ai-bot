"""Seed (or promote) the admin user from settings. Run: `python -m app.seed_admin`.

Idempotent: creates the admin if missing, otherwise promotes the existing account and
(re)sets its password to ADMIN_PASSWORD so the configured credentials always work.
"""

import asyncio

from .auth import get_password_hash
from .config import settings
from .crud import create_user, get_user_by_email
from .database import AsyncSessionLocal
from .models import Role
from .schemas import UserCreate


async def seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, settings.ADMIN_EMAIL)
        created = user is None
        if user is None:
            user = await create_user(
                db,
                UserCreate(
                    email=settings.ADMIN_EMAIL,
                    password=settings.ADMIN_PASSWORD,
                    full_name=settings.SEED_ADMIN_NAME,
                ),
            )
        else:
            # Ensure the configured password works even if the account already existed.
            user.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            if settings.SEED_ADMIN_NAME:
                user.full_name = settings.SEED_ADMIN_NAME

        user.role = Role.admin
        user.is_verified = True
        await db.commit()
        action = "created" if created else "promoted"
        print(f"admin {action}: {settings.ADMIN_EMAIL} (role=admin, verified, password set)")


if __name__ == "__main__":
    asyncio.run(seed_admin())

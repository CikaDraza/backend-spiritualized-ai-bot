"""Seed (or promote) the admin user from settings. Run: `python -m app.seed_admin`."""

import asyncio

from .config import settings
from .crud import create_user, get_user_by_email
from .database import AsyncSessionLocal
from .models import Role
from .schemas import UserCreate


async def seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, settings.ADMIN_EMAIL)
        if user is None:
            user = await create_user(
                db,
                UserCreate(
                    email=settings.ADMIN_EMAIL,
                    password=settings.ADMIN_PASSWORD,
                    full_name="Admin",
                ),
            )
        user.role = Role.admin
        user.is_verified = True
        await db.commit()
        print(f"admin ready: {settings.ADMIN_EMAIL} (role=admin, verified)")


if __name__ == "__main__":
    asyncio.run(seed_admin())

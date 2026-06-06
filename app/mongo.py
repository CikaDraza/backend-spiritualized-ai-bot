from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
mongo_db = mongo_client[settings.MONGODB_DB]


async def log_chat_message(
    user_id: int | None,
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    document = {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "created_at": datetime.utcnow(),
    }
    await mongo_db.chat_logs.insert_one(document)

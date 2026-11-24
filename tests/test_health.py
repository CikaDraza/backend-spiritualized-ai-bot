import asyncio
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app import database, health
from app.main import app


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.head = ScriptDirectory.from_config(
            Config(str(Path(health.__file__).resolve().parent.parent / "alembic.ini"))
        ).get_current_head()
        self.assertIsNotNone(self.head)
        self.ping = MagicMock()
        self.ping.scalar_one.return_value = 1
        self.versions = MagicMock()
        self.versions.scalars.return_value = [self.head]
        self.connection = AsyncMock(spec=AsyncConnection)
        self.connection.__aenter__.return_value = self.connection
        self.connection.execute.side_effect = [self.ping, self.versions]
        engine_patch = patch.object(database, "engine", spec=AsyncEngine)
        self.connect = engine_patch.start().connect
        self.connect.return_value = self.connection
        self.addCleanup(engine_patch.stop)
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def assert_unavailable(self):
        with self.assertLogs("spiritualized.health", level="WARNING") as logs:
            response = await self.client.get("/health/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        return " ".join(logs.output)

    async def test_ready_without_authentication_only_reads_database(self):
        response = await self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.connect.assert_called_once_with()
        self.assertEqual(
            [str(call.args[0]) for call in self.connection.execute.await_args_list],
            ["SELECT 1", "SELECT version_num FROM alembic_version"],
        )
        self.connection.commit.assert_not_awaited()
        self.connection.__aexit__.assert_awaited_once()

    async def test_database_connection_failure_is_sanitized(self):
        self.connection.__aenter__.side_effect = RuntimeError("private-database-details")
        logs = await self.assert_unavailable()
        self.assertIn("RuntimeError", logs)
        self.assertNotIn("private-database-details", logs)

    async def test_failed_ping(self):
        self.connection.execute.side_effect = RuntimeError("database unavailable")
        await self.assert_unavailable()
        self.assertEqual(self.connection.execute.await_count, 1)
        self.connection.__aexit__.assert_awaited_once()

    async def test_unexpected_ping_result(self):
        self.ping.scalar_one.return_value = 0
        await self.assert_unavailable()
        self.assertEqual(self.connection.execute.await_count, 1)

    async def test_revision_must_be_exactly_one_current_head(self):
        for revisions in ([], ["older-revision"], ["unknown-revision"], [self.head, "extra"]):
            with self.subTest(revisions=revisions):
                self.connection.execute.side_effect = [self.ping, self.versions]
                self.versions.scalars.return_value = revisions
                logs = await self.assert_unavailable()
                self.assertIn("not at head", logs)

    async def test_missing_alembic_version_table(self):
        self.connection.execute.side_effect = [self.ping, RuntimeError("missing table")]
        await self.assert_unavailable()

    async def test_migration_configuration_failure(self):
        with patch.object(health.ScriptDirectory, "from_config", side_effect=RuntimeError):
            await self.assert_unavailable()
        self.connect.assert_not_called()

    async def test_missing_or_ambiguous_migration_head(self):
        with patch.object(health.ScriptDirectory, "from_config") as scripts:
            scripts.return_value.get_current_head.return_value = None
            await self.assert_unavailable()
            scripts.return_value.get_current_head.side_effect = RuntimeError("multiple heads")
            await self.assert_unavailable()
        self.connect.assert_not_called()

    async def test_database_timeout_covers_connection_and_both_queries(self):
        async def slow(*args, **kwargs):
            await asyncio.sleep(30)

        for stage in ("connect", "ping", "version"):
            with self.subTest(stage=stage):
                self.connection.__aenter__.side_effect = slow if stage == "connect" else None

                async def execute(statement):
                    if stage == "ping" or str(statement).startswith("SELECT version_num"):
                        await slow()
                    return self.ping

                self.connection.execute.side_effect = execute
                started = time.monotonic()
                logs = await self.assert_unavailable()
                self.assertLess(time.monotonic() - started, 4.5)
                self.assertIn("exceeded 3 seconds", logs)

    async def test_existing_root_response_is_unchanged(self):
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()

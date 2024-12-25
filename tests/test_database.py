import asyncio
import datetime
import unittest

from pastrami.database import Database, DuplicatedItemException


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.database = Database("sqlite:///:memory:", create=True, echo=False)
        asyncio.run(self.database.connect())

    async def test_connect(self):
        async with Database("postgresql://127.0.0.1:65535") as database:
            with self.assertRaises(ConnectionRefusedError):
                await database.get_salt()

        with self.assertRaises(ValueError):
            Database("-> wrong <-://127.0.0.1:65535")

    async def test_database_methods(self):
        text = await self.database.add_text(
            {
                "text_id": "DUPLICATED",
                "content": "FooBar",
                "created": "1970-01-01 00:00:00",
            }
        )
        self.assertEqual(
            text,
            {
                "text_id": "DUPLICATED",
                "content": "FooBar",
                "created": datetime.datetime(1970, 1, 1, 0, 0),
            },
        )

        with self.assertRaises(DuplicatedItemException):
            await self.database.add_text(
                {
                    "text_id": "DUPLICATED",
                    "content": "FooBar",
                    "created": "1970-01-01 00:00:00",
                }
            )

        expired = await self.database.purge_expired(1)
        self.assertEqual(expired, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

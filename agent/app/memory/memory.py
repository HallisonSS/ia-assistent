import asyncpg

from app.config import load_settings


class Memory:

    def __init__(self):

        settings = load_settings()

        self.database_url = (
            settings.database_url
        )

    async def connect(self):

        return await asyncpg.connect(
            self.database_url
        )

    async def initialize(self):

        conn = await self.connect()

        try:

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS
                conversation_messages (

                    id BIGSERIAL PRIMARY KEY,

                    session_id TEXT NOT NULL,

                    role TEXT NOT NULL,

                    content TEXT NOT NULL,

                    created_at TIMESTAMPTZ
                    DEFAULT NOW()
                );
                """
            )

        finally:

            await conn.close()

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str
    ):

        conn = await self.connect()

        try:

            await conn.execute(
                """
                INSERT INTO
                conversation_messages
                (
                    session_id,
                    role,
                    content
                )
                VALUES ($1, $2, $3)
                """,
                session_id,
                role,
                content
            )

        finally:

            await conn.close()

    async def get_history(
        self,
        session_id: str,
        limit: int = 10
    ):

        conn = await self.connect()

        try:

            rows = await conn.fetch(
                """
                SELECT
                    role,
                    content
                FROM conversation_messages

                WHERE session_id = $1

                ORDER BY created_at DESC

                LIMIT $2
                """,
                session_id,
                limit
            )

            rows = list(reversed(rows))

            return [
                {
                    "role": row["role"],
                    "content": row["content"]
                }

                for row in rows
            ]

        finally:

            await conn.close()

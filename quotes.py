import asyncio
import random

import aiosqlite


async def init_db():
    async with aiosqlite.connect("databases/quotes.db") as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS quotes
            (
                id INTEGER PRIMARY KEY,
                quote TEXT UNIQUE,
            )"""
        )
        await conn.commit()


asyncio.run(init_db())


async def get_quote() -> str | None:
    async with aiosqlite.connect("databases/quotes.db") as conn:
        async with conn.execute("SELECT id FROM quotes ORDER BY id DESC") as cur:
            result = await cur.fetchone()
            if not result:
                return None
            max_id = result[0]
            id = random.randint(0, max_id)
            async with conn.execute("SELECT quote FROM quotes WHERE id=?", (id,)) as curr:
                quote = await curr.fetchone()
                if not quote:
                    return None
                return quote[0]

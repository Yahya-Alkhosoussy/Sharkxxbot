import asyncio

import aiosqlite


async def init_db():
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS shark_tooth
            (
                username TEXT,
                user_id INTEGER PRIMARY KEY,
                count INTEGER
            )"""
        )
        await conn.commit()


asyncio.run(init_db())


async def add_user_to_shark_tooth(username: str, user_id: int):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO shark_tooth (username, user_id, count) VALUES (?, ?, ?)", (username, user_id, 1)
        )
        await conn.commit()


async def is_user_in_db(user_id: int):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        async with conn.execute("SELECT COUNT(*) FROM shark_tooth WHERE user_id=?", (user_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            count = result[0]
            if count >= 1:
                return True
            return False


async def add_shark_tooth(username: str, user_id: int):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute("UPDATE shark_tooth SET count=count+1 WHERE user_id=?", (user_id,))
        changed = await check_for_username_change(username, user_id)
        if changed:
            await change_username(username, user_id)
        await conn.commit()


async def check_for_username_change(username: str, user_id: int) -> None | bool:
    async with aiosqlite.connect("databases/redeems.db") as conn:
        async with conn.execute("SELECT username FROM shark_tooth WHERE user_id=?", (user_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            name = result[0]
            if name == username:
                return False
            return True


async def change_username(username: str, user_id: int):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute("UPDATE shark_tooth SET username=? WHERE user_id=?", (username, user_id))

        await conn.commit()

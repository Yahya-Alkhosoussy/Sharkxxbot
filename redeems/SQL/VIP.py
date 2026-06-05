import asyncio

import aiosqlite


async def init_db():
    async with aiosqlite.connect("databases/VIP_list.db") as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS vips
            (
                id INTEGER PRIMARY KEY,
                twitch_name TEXT NOT NULL,
                twitch_id INTEGER NOT NULL,
                discord_name TEXT DEFAULT NULL,
                discord_id INTEGER DEFAULT NULL
            )"""
        )
        await conn.commit()


asyncio.run(init_db())


async def add_user_to_VIP(twitch_username: str, twitch_id: int):
    async with aiosqlite.connect("database/VIP_list.db") as conn:
        await conn.execute("INSERT OR IGNORE INTO vips (twitch_name, twitch_id) VALUES (?, ?)", (twitch_username, twitch_id))
        await conn.commit()

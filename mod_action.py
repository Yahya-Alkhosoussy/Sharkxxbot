import asyncio
from datetime import datetime

import aiosqlite


async def init_db():
    async with aiosqlite.connect("databases/mod_actions.db") as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS bans
                (
                    id INTEGER PRIMARY KEY,
                    streamer TEXT NOT NULL,
                    banned_user TEXT NOT NULL,
                    banned_user_id INTEGER NOT NULL,
                    reason TEXT DEFAULT NULL,
                    mod_that_banned_them TEXT NOT NULL,
                    when_banned TEXT NOT NULL,
                    UNIQUE(streamer, banned_user)
                )
            """
        )
        await conn.commit()


asyncio.run(init_db())


async def add_ban(
    streamer: str, banned_user: str, banned_user_id: int, reason: str | None, mod_that_banned_them: str, when_banned: datetime
):
    when_str = when_banned.strftime(r"%Y-%m-%d %H:%M")
    async with aiosqlite.connect("databases/mod_actions.db") as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO bans (streamer, banned_user, reason, mod_that_banned_them, when_banned)"
            " VALUES (?, ?, ?, ?, ?)",
            (streamer, banned_user, reason, mod_that_banned_them, when_str),
        )
        await conn.commit()
        if streamer == "sharkocalypse":
            await add_ban("dyslexxik", banned_user, banned_user_id, reason, mod_that_banned_them, when_banned)
        elif streamer == "dyslexxik":
            await add_ban("sharkocalypse", banned_user, banned_user_id, reason, mod_that_banned_them, when_banned)


async def get_banned_users(streamer: str):
    async with aiosqlite.connect("databases/mod_actions.db") as conn:
        async with conn.execute("SELECT banned_user FROM bans WHERE streamer=?", (streamer,)) as cur:
            results = await cur.fetchall()
            banned_users: list[str] = []
            for user in results:
                banned_users.append(str(user[0]))

            return banned_users


async def remove_ban(streamer: str, banned_user: str):
    async with aiosqlite.connect("databases/mod_actions.db") as conn:
        await conn.execute("DELETE FROM bans WHERE banned_user=? AND streamer=?", (banned_user, streamer))
        if streamer == "sharkocalypse":
            await conn.execute("DELETE FROM bans WHERE banned_user=? AND streamer=?", (banned_user, "dyslexxik"))
        elif streamer == "dyslexxik":
            await conn.execute("DELETE FROM bans WHERE banned_user=? AND streamer=?", (banned_user, "sharkocalypse"))
        await conn.commit()

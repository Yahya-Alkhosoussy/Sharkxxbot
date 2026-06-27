from asyncio import run
from pathlib import Path

from aiosqlite import connect

from utils.core import GiftedSub, TwitchUser

db_dir = Path("databases")
if not db_dir.exists():
    db_dir.mkdir()
db_path = db_dir / "gifted_subs.db"


async def init_db():
    async with connect(db_path) as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS gifted
            (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                twitch_id TEXT UNIQUE NOT NULL,
                gifted_count INTEGER DEFAULT 0
            )"""
        )
        await conn.commit()


run(init_db())


async def add_gifted_user(user: TwitchUser):
    async with connect(db_path) as conn:
        await conn.execute("INSERT OR IGNORE INTO gifted (name, twitch_id) VALUES (?, ?)", (user.login, user.id))
        await conn.commit()


async def is_user_in_db(user: TwitchUser):
    async with connect(db_path) as conn:
        async with conn.execute("SELECT COUNT(*) FROM gifted WHERE twitch_id=?", (user.id)) as cur:
            result = await cur.fetchone()
            if result is None:
                return False
            if result[0] == 0:
                return False
            return True


async def update_gifted_count(sub: GiftedSub):
    await check_for_username_changed(sub.user)
    async with connect(db_path) as conn:
        await conn.execute("UPDATE gifted SET gifted_count=gifted_count+? WHERE twitch_id=?", (sub.gifted_count, sub.user.id))
        await conn.commit()


async def check_for_username_changed(user: TwitchUser):
    async with connect(db_path) as conn:
        async with conn.execute("SELECT name FROM gifted WHERE twitch_id=?", (user.id)) as cur:
            result = await cur.fetchone()
            if result is None:
                raise Exception("Name not found")
        name: str = result[0]
        if name.lower() != user.login:
            await conn.execute("UPDATE gifted SET name=? WHERE twitch_id=?", (user.login, user.id))
        await conn.commit()


async def get_gifted_count(user: TwitchUser) -> int:
    await check_for_username_changed(user)
    async with connect(db_path) as conn:
        async with conn.execute("SELECT gifted_count FROM gifted WHERE twitch_id=?", (user.id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                raise ValueError("Could not find gift count")
            return result[0]

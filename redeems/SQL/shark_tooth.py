import asyncio

import aiosqlite


async def init_db():
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS shark_tooth
            (
                username TEXT,
                user_id INTEGER,
                type TEXT,
                count INTEGER DEFAULT 0,
                UNIQUE(user_id, type)
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS crystals
            (
                name TEXT PRIMARY KEY
            )"""
        )
        await conn.commit()


asyncio.run(init_db())


async def add_user_to_shark_tooth(username: str, user_id: int, crystal: str):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO shark_tooth (username, user_id, type, count) VALUES (?, ?, ?, ?)",
            (username, user_id, crystal, 1),
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


async def add_shark_tooth(username: str, user_id: int, crystal: str):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        async with conn.execute("SELECT COUNT(*) FROM shark_tooth WHERE user_id=? AND type=?", (user_id, crystal)) as cur:
            count = await cur.fetchone()
            if count is None:
                return
            count = count[0]
        if count != 0:
            await conn.execute("UPDATE shark_tooth SET count=count+1 WHERE user_id=?", (user_id,))
            changed = await check_for_username_change(username, user_id, conn)
            if changed:
                await change_username(username, user_id, conn)
            await conn.commit()
        else:
            await conn.execute(
                "INSERT OR IGNORE INTO shark_tooth (username, user_id, type, count) VALUES (?, ?, ?, ?)",
                (username, user_id, crystal, 1),
            )
            changed = await check_for_username_change(username, user_id, conn)
            if changed:
                await change_username(username, user_id, conn)
            await conn.commit()


async def check_for_username_change(username: str, user_id: int, conn: aiosqlite.Connection) -> None | bool:
    async with conn.execute("SELECT username FROM shark_tooth WHERE user_id=?", (user_id,)) as cur:
        result = await cur.fetchone()
        if result is None:
            return None
        name = result[0]
        if name == username:
            return False
        return True


async def change_username(username: str, user_id: int, conn: aiosqlite.Connection):
    await conn.execute("UPDATE shark_tooth SET username=? WHERE user_id=?", (username, user_id))

    await conn.commit()


async def get_crystal_list():
    async with aiosqlite.connect("databases/redeems.db") as conn:
        async with conn.execute("SELECT name FROM crystals") as cur:
            crystals = await cur.fetchall()
            return crystals


async def add_crystal(crystal_name: str):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute("INSERT OR IGNORE INTO crystals (name) VALUES (?)", (crystal_name,))
        await conn.commit()


names = [
    "Clear Quartz",
    "Amethyst",
    "Rose Quartz",
    "Citrine",
    "Black Tourmaline",
    "Selenite",
    "Carnelian",
    "Lapis Lazuli",
    "Green Aventurine",
    "Fluorite ",
    "Bloodstone",
    "Red Jasper",
    "Agate",
    "Ametrine",
    "Ancestralite",
    "Apophyllite",
    "Aquamarine",
    "Aragonite",
    "Calcite",
    "Copper",
    "Coppernite",
    "Emerald",
    "Fluorite",
    "Garnet",
    "Himalayan Salt",
    "Iolite",
    "Jade",
    "Kunzite",
    "Labradorite",
    "Lapis Lazuli",
    "Moonstone",
    "Morganite",
    "Muscovite",
    "Black Obsidian",
    "Black Onyx",
    "Opal",
    "Petalite",
    "Pyrite",
    "Clear Quartz",
    "Fire Quartz",
    "Rhodonite",
    "Ruby",
    "Pink Sapphire",
    "Tanzanite",
    "Tiger's Eye",
    "Turquoise",
]

for name in names:
    asyncio.run(add_crystal(name))

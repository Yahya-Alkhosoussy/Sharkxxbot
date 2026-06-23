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
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS tooth_messages
            (
                id INTEGER PRIMARY KEY,
                message TEXT UNIQUE
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


async def get_crystal_count(user_id: int) -> int | None:
    async with aiosqlite.connect("databases/redeems.db") as conn:
        async with conn.execute("SELECT COUNT(*) FROM crystals WHERE user_id=?", (user_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return
            return result[0]


async def get_messages():
    async with aiosqlite.connect("databases/redeems.db") as conn:
        async with conn.execute("SELECT message FROM tooth_messages") as cur:
            messages = await cur.fetchall()
            return list(messages)


async def add_message(message: str):
    async with aiosqlite.connect("databases/redeems.db") as conn:
        await conn.execute("INSERT OR IGNORE INTO tooth_messages (message) VALUES (?)", (message,))
        await conn.commit()


if __name__ == "__main__":
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
        crystal_list = list(asyncio.run(get_crystal_list()))
        if name in crystal_list:
            continue
        asyncio.run(add_crystal(name))

    messages = [
        "You reach into the abyss and feel a sharp prick... a tithe has been paid.  A (crystal type) shark tooth appears as a gift from the deep.",  # noqa
        "You reach into the abyss and lose something you can't quite name. In return, you gain a (crystal type) shark tooth. Something tries to convince you it was a fair trade.",  # noqa
        "You reach into the abyss. Something sharp brushes your fingertip. Moments later, a  (crystal type) shark tooth finds its way into your possession. Entirely unrelated, surely.",  # noqa
        "The sting is brief, almost polite. When it fades, a  (crystal type) shark tooth is already in your possession. The Deep continues without comment.",  # noqa
        "The drop is taken, but the sensation lingers longer than it should, like an echo underwater. A (crystal type) shark tooth surfaces afterward.",  # noqa
        "Something is taken that cannot be named. In exchange, a (crystal type) shark tooth floats towards you.",
        "Something is quietly collected from you by the abyss. You’re not sure what. A (crystal type) shark tooth is left behind.",  # noqa
        "A crimson offering sinks into unseen depths. Moments later, a (crystal type) shark tooth surfaces.",
        "No one remembers placing the (crystal type) shark tooth in your hand. Best not to ask.",
        "The tides whisper among themselves before surrendering a (crystal type) shark tooth.",
        "A bargain is acknowledged. The terms are unclear, but a (crystal type) shark tooth has been delivered.",
        "Your tithe causes a momentary desync between you and reality. When things resync, you have a (crystal type) shark tooth.",  # noqa
        "Something stirs beneath the dark waters. When the ripples settle, a (crystal type) shark tooth remains.",
        "You reach into the abyss. The darkness rummages through your pockets. Suddenly they feel... lighter. You are given a (crystal type) shark tooth in return.",  # noqa
        "You reach into the abyss. A moment passes. When your hand returns, it carries a (crystal type) shark tooth... and a secret you'll remember later.",  # noqa
        "You reach into the abyss. Something wraps around your hand gently. When you pull it back, a (crystal type) shark tooth rests in your palm. Curious.",  # noqa
        "You reach into the abyss and feel a sharp prick upon your finger. Something unseen drinks a drop of your essence. A trade has been accepted... In return, you receive a (crystal type) shark tooth.",  # noqa
    ]

    for message in messages:
        current_messages = asyncio.run(get_messages())
        if message in current_messages:
            continue
        asyncio.run(add_message(message))

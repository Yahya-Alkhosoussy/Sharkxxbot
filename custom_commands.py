import asyncio

import aiosqlite

DB_PATH = "databases/chat_commands.db"


async def init_db():
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("""CREATE TABLE IF NOT EXISTS commands
                (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE, -- the name of the command
                    reply TEXT, -- what the bot should reply with
                    user_level str -- what's the minimum level the user needs in order to use it
                )""")
    await conn.commit()


"""
Expanding on user_level:

User level is the role of the user in the community, so for example are they just a viewer?
Are they a moderator? Are they the streamer themselves? Is it a sub only command?
"""


async def add_command(command_name: str, command_reply: str, user_level: str):
    name = "!" + command_name
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO commands (name, reply, user_level) VALUES (?, ?, ?)", (name, command_reply, user_level)
        )
        await conn.commit()


async def edit_command_reply(command_id: int, command_reply: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE commands SET reply=? WHERE id=?", (command_reply, command_id))
        await conn.commit()


async def check_for_command(command_name: str) -> str | bool:
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT reply FROM commands WHERE name=?", (command_name,)) as cur:
            reply = await cur.fetchone()
            if reply:
                return reply[0]
    return False


async def get_command_list():
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT name, reply, user_level FROM commands") as cur:
            commands = await cur.fetchall()
            if commands:
                command_names: list[str] = []
                command_replies: list[str] = []
                command_user_levels: list[str] = []
                for command in commands:
                    command_names.append(command[0])
                    command_replies.append(command[1])
                    command_user_levels.append(command[2])
                return command_names, command_replies, command_user_levels
            return None


asyncio.run(init_db())
asyncio.run(add_command("hello", "hello there!", "everyone"))
print(asyncio.run(get_command_list()))

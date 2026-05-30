# This is where the database interactions are
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import aiosqlite

base_db_path = Path(__file__).parent.parent / "Shark-Bot" / "databases"
shark_file_path = base_db_path / "shark_game.db"


async def get_shark_names() -> set[str]:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT name FROM sharks") as cur:
            results = await cur.fetchall()
            names: set[str] = set()
            for name in results:
                names.add(name[0])
            return names


async def get_shark_fact(shark_name: str) -> str | None:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT fact FROM sharks WHERE name=?", (shark_name,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            return result[0]


async def get_shark_weight(shark_name: str) -> int | None:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT weight FROM sharks WHERE name=?", (shark_name,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            return result[0]


class SharkRarity(Enum):
    VERY_COMMON = 1
    COMMON = 2
    UNCOMMON = 3
    RARE = 4
    ULTRA_RARE = 5


async def get_shark_names_rarity(rarity: SharkRarity) -> set[str]:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT name FROM sharks WHERE rarity=?", (rarity.value,)) as cur:
            results = await cur.fetchall()
            names: set[str] = set()
            for name in results:
                names.add(name[0])
            return names


async def get_latest_twitch_catch(twitch_id: int):
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute(
            "SELECT time FROM dex WHERE caught_on=? AND twitch_id=? ORDER BY id DESC LIMIT 1", ("twitch", twitch_id)
        ) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            time = datetime.strptime(result[0], r"%Y-%m-%d %H")
            return time


async def is_daily_catch_done(twitch_id: int):
    latest_catch = await get_latest_twitch_catch(twitch_id)
    if latest_catch is None:
        return None
    delta = datetime.now() - latest_catch
    if delta >= timedelta(hours=16):
        return False
    return True


async def get_shark_names_caught(twitch_id: int) -> set[str]:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT shark FROM dex WHERE twitch_id=?", (twitch_id,)) as cur:
            results = await cur.fetchall()
            names: set[str] = set()
            for name in results:
                names.add(name[0])
            return names


async def get_feed_info(twitch_id: int) -> tuple[str | None, int] | None:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute(
            "SELECT last_fed, fed_streak FROM dex WHERE twitch_id=? ORDER BY id DESC limit 1", (twitch_id,)
        ) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            last_fed = result[0]
            fed_streak = result[1]
            return last_fed, fed_streak


async def set_feed_info(twitch_id: int, last_fed: datetime, fed_streak: int) -> bool:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT id FROM dex WHERE twitch_id=? ORDER BY id DESC limit 1", (twitch_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return False
            row_id = result[0]
            await conn.execute(
                "UPDATE dex SET last_fed=?, fed_streak=? WHERE id=?", (last_fed.strftime(r"%Y-%m-%d"), fed_streak, row_id)
            )
            await conn.commit()
            return True


async def catch_shark(twitch_id: int, twitch_username: str, when_caught: datetime, shark_caught: str, rarity: str):
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT user_id, username FROM dex WHERE twitch_id=? ORDER BY id LIMIT 1", (twitch_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return False
            discord_id: int = result[0]
            discord_name: str = result[1]
            fact = await get_shark_fact(shark_caught)
            weight = await get_shark_weight(shark_caught)
            coins = await check_currency(twitch_id)
            feed_info = await get_feed_info(twitch_id)
            last_fed, fed_streak = feed_info if feed_info else (None, 0)
            await conn.execute(
                "INSERT OR IGNORE INTO dex "
                """(
                    user_id,
                    username,
                    shark,
                    time,
                    fact,
                    weight,
                    coins,
                    rarity,
                    caught_on,
                    fed_streak,
                    twitch_id,
                    twitch_user,
                    last_fed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    discord_id,
                    discord_name,
                    shark_caught,
                    when_caught.strftime(r"%Y-%m-%d %H"),
                    fact,
                    weight,
                    coins,
                    rarity,
                    "twitch",
                    fed_streak,
                    twitch_id,
                    twitch_username,
                    last_fed,
                ),
            )
            await conn.commit()
            return True


async def check_currency(twitch_id: int) -> int:
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT coins FROM dex WHERE twitch_id=? ORDER BY id DESC limit 1", (twitch_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return 0
            return result[0]


async def add_coins(twitch_id: int, amount_to_add: int):
    coins = await check_currency(twitch_id)
    coins_to_give = coins + amount_to_add
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT id FROM dex WHERE twitch_id=? ORDER BY id DESC limit 1", (twitch_id,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            table_id = result[0]
            await conn.execute("UPDATE dex SET coins=? WHERE id=?", (coins_to_give, table_id))
            await conn.commit()


async def get_shark_rarity(shark_name: str):
    async with aiosqlite.connect(shark_file_path) as conn:
        async with conn.execute("SELECT rarity FROM sharks WHERE name=?", (shark_name,)) as cur:
            result = await cur.fetchone()
            if result is None:
                return None
            return result[0]


async def reward_coins(twitch_id: int, rarity: str, shark_name: str) -> int:
    find_rarity = await get_shark_rarity(shark_name)
    retVal = 0
    match rarity:
        case "normal":
            match find_rarity:
                case 1:  # very common
                    await add_coins(twitch_id, 10)
                    retVal = 10
                case 2:  # common
                    await add_coins(twitch_id, 15)
                    retVal = 15
                case 3:  # uncommon
                    await add_coins(twitch_id, 20)
                    retVal = 20
                case 4:  # rare
                    await add_coins(twitch_id, 25)
                    retVal = 25
                case 5:  # ultra-rare
                    await add_coins(twitch_id, 30)
                    retVal = 30
        case "shiny":
            match find_rarity:
                case 1:  # very common
                    await add_coins(twitch_id, 20)
                    retVal = 20
                case 2:  # common
                    await add_coins(twitch_id, 25)
                    retVal = 25
                case 3:  # uncommon
                    await add_coins(twitch_id, 30)
                    retVal = 30
                case 4:  # rare
                    await add_coins(twitch_id, 35)
                    retVal = 35
                case 5:  # ultra-rare
                    await add_coins(twitch_id, 40)
                    retVal = 40
        case "legendary":
            match find_rarity:
                case 1:  # very common
                    await add_coins(twitch_id, 30)
                    retVal = 30
                case 2:  # common
                    await add_coins(twitch_id, 35)
                    retVal = 35
                case 3:  # uncommon
                    await add_coins(twitch_id, 40)
                    retVal = 40
                case 4:  # rare
                    await add_coins(twitch_id, 45)
                    retVal = 45
                case 5:  # ultra-rare
                    await add_coins(twitch_id, 50)
                    retVal = 50
    return retVal

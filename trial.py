import asyncio
from pathlib import Path

import aiosqlite

file_path = Path(__file__)
database = file_path.parent.parent / "Shark-Bot" / "databases" / "shark_game.db"
print(database.exists())


async def connect_to_db():
    async with aiosqlite.connect(database) as conn:
        async with conn.execute("SELECT fact FROM sharks") as cur:
            results = await cur.fetchall()
            facts = []
            for result in results:
                facts.append(result[0])
                print(f"{result[0]}\n")
            print(facts)


asyncio.run(connect_to_db())

# This is where all the catching logic lives
from asyncio import run  # noqa
from datetime import datetime
from random import choice, randint
from typing import Literal
from pathlib import Path

import matplotlib.pyplot as plt


from shark_db_interaction import (
    SharkRarity,
    get_feed_info,
    get_shark_names,
    get_shark_names_caught,
    get_shark_names_rarity,
    set_feed_info,
)

DEBUG = True


async def get_sharks_after_rarity() -> tuple[set[str], str]:
    init_rarity = randint(0, 100)
    if init_rarity <= 3:
        list_of_names = await get_shark_names_rarity(SharkRarity.ULTRA_RARE)
        rarity = "ultra rare"
    elif init_rarity <= 20:
        list_of_names = await get_shark_names_rarity(SharkRarity.RARE)
        rarity = "rare"
    elif init_rarity <= 35:
        list_of_names = await get_shark_names_rarity(SharkRarity.UNCOMMON)
        rarity = "uncommon"
    elif init_rarity <= 65:
        list_of_names = await get_shark_names_rarity(SharkRarity.COMMON)
        rarity = "common"
    else:
        list_of_names = await get_shark_names_rarity(SharkRarity.VERY_COMMON)
        rarity = "very common"

    return list_of_names, rarity


def graph_rarities(rarities: dict, limit: int):
    labels = list(rarities.keys())
    values = list(rarities.values())

    plt.bar(labels, values, color="steelblue")
    plt.title("Shark Rarity Distribution")
    plt.xlabel("Rarity")
    plt.ylabel("Count")
    plt.tight_layout()
    dir = Path("test images")
    if not dir.exists():
        dir.mkdir()
    plt.savefig(f"test images/rarities_{limit}.png")


async def run_and_graph_data(limit: int):
    rarities: dict[str, int] = {}
    for _ in range(limit):
        _, rarity = await get_sharks_after_rarity()
        if not rarities.get(rarity):
            rarities[rarity] = 1
        else:
            rarities[rarity] += 1

    graph_rarities(rarities, limit)


if DEBUG:
    limits = [10, 100, 1000, 10000]
    for limit in limits:
        run(run_and_graph_data(limit))


async def choose_shark_for_catch():
    list_of_names, _ = await get_sharks_after_rarity()
    name_to_drop = choice(list(list_of_names))
    rarity_rand = randint(0, 100)
    if rarity_rand <= 2:
        rarity = "legendary"
    elif rarity_rand <= 5:
        rarity = "shiny"
    else:
        rarity = "normal"

    return name_to_drop, rarity


async def get_sharkpct(twitch_id: int) -> tuple[float, int, int]:
    sharks = await get_shark_names()
    sharks_caught = await get_shark_names_caught(twitch_id)
    total_sharks = len(sharks)
    total_caught = len(sharks_caught)
    pct = (total_caught / total_sharks * 100.0) if total_sharks else 0.0
    return pct, total_sharks, total_caught


async def get_missing_shark_names(twitch_id: int) -> set[str]:
    sharks = await get_shark_names()
    sharks_caught = await get_shark_names_caught(twitch_id)
    sharks_not_caught: set[str] = set()
    for shark in sharks:
        if shark not in sharks_caught:
            sharks_not_caught.add(shark)
    return sharks_not_caught


async def compute_mood(last_fed: str | None, streak: int) -> Literal["hungry", "neutral", "curious", "excited", "happy"]:
    """
    Rules:
        - if last fed >= 2 days ago => hungry
        - if fed today and streak is greater than 2 then happy
        - else it's neutral
    """
    today = datetime.now().date()
    if not last_fed:
        return "neutral"
    try:
        last_date = datetime.strptime(last_fed, r"%Y-%m-%d").date()
    except Exception:
        return "neutral"

    diff = (today - last_date).days
    if diff >= 2:
        return "hungry"
    if diff == 0:
        if streak <= 5:
            return "neutral"
        elif streak <= 15:
            return "curious"
        elif streak <= 25:
            return "excited"
        else:
            return "happy"
    return "neutral"


async def feed_sharks(
    twitch_id: int,
) -> None | tuple[None | Literal["hungry", "neutral", "curious", "excited", "happy"], bool, None | str]:
    """This function returns whether to post an early message or a feed message"""
    info = await get_feed_info(twitch_id)
    if info is not None:
        last_fed, fed_streak = info
        try:
            if last_fed:
                today = datetime.now().date()
                last_fed = datetime.strptime(last_fed, r"%Y-%m-%d").date()
                delta = (today - last_fed).days
            else:
                delta = 9999
        except Exception:
            delta = 9999

        was_hungry = delta >= 2

        if delta == 0 and last_fed:
            if isinstance(last_fed, str):
                mood_now = await compute_mood(last_fed, fed_streak)
            else:
                mood_now = await compute_mood(last_fed.strftime(r"%Y-%m-%d"), fed_streak)
            early_message = True
            return mood_now, early_message, None

        if delta == 1 and fed_streak > 0:
            fed_streak += 1
        else:
            fed_streak = 1

        if isinstance(last_fed, datetime):
            fed = await set_feed_info(twitch_id, last_fed, fed_streak)
        elif isinstance(last_fed, str):
            fed = await set_feed_info(twitch_id, datetime.strptime(last_fed, r"%Y-%m-%d"), fed_streak)
        else:
            fed = await set_feed_info(twitch_id, datetime.now(), 1)

        if not fed:
            return None, False, None

        if was_hungry:
            mood_now = "neutral"
            early_message = False
            return mood_now, early_message, "They were Hungry; today's feed calmed them down."
        else:
            if fed_streak >= 26:
                mood_now = "happy"
                early_message = False
                return mood_now, early_message, f"{fed_streak} streams in a row — your sharks are thriving!"
            elif fed_streak >= 16:
                mood_now = "excited"
                early_message = False
                return mood_now, early_message, f"{fed_streak} streams in a row — your sharks are thriving!"
            elif fed_streak >= 6:
                mood_now = "curious"
                early_message = False
                return mood_now, early_message, f"{fed_streak} streams in a row — your sharks are thriving!"
            else:
                mood_now = "neutral"
                early_message = False
                return mood_now, early_message, "Feed again next couple of streams to change how they feel."

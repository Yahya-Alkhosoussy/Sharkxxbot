from random import choice

from redeems.SQL.shark_tooth import (
    add_shark_tooth,
    add_user_to_shark_tooth,
    get_crystal_count,
    get_crystal_list,
    get_messages,
    is_user_in_db,
)
from redeems.SQL.VIP import add_user_to_VIP


async def deal_with_sharktooth(username: str, user_id: int):
    is_in_db = await is_user_in_db(user_id)

    crystal_list = await get_crystal_list()

    crystal: str = choice(list(crystal_list))[0]

    message_list = await get_messages()
    message: str = choice(message_list)[0]

    message = message.replace("(crystal type)", crystal.lower())

    if is_in_db:
        await add_shark_tooth(username, user_id, crystal)
    else:
        await add_user_to_shark_tooth(username, user_id, crystal)

    crystal_count = await get_crystal_count(user_id)

    if crystal_count:
        tooth_or_teeth = "shark teeth" if crystal_count > 1 or crystal_count == 0 else "shark tooth"
        message += f"@{username} you have {crystal_count} {tooth_or_teeth}"
    else:
        message += f"@{username}"

    return message


async def deal_with_VIP(username: str, user_id: int):
    await add_user_to_VIP(username, user_id)

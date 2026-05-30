from redeems.SQL.shark_tooth import add_shark_tooth, add_user_to_shark_tooth, is_user_in_db
from redeems.SQL.VIP import add_user_to_VIP


async def deal_with_sharktooth(username: str, user_id: int):
    is_in_db = await is_user_in_db(user_id)
    if is_in_db:
        await add_shark_tooth(username, user_id)
    else:
        await add_user_to_shark_tooth(username, user_id)


async def deal_with_VIP(username: str, user_id: int):
    await add_user_to_VIP(username, user_id)

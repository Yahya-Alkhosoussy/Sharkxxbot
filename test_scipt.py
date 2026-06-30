import asyncio

from main import APP_ID, APP_SECRET, TARGET_CHANNEL, USER_SCOPE, SharkBot

bot = SharkBot(APP_ID, APP_SECRET, USER_SCOPE, TARGET_CHANNEL)  # type: ignore


def get_rewards(start: int, end: int):

    rewards = asyncio.run(bot.calculate_rewards(start, end))

    print(f"CASE WHERE SOMEONE STARTED WITH {start} SUBS GIFTED {end - start} SUBS")

    msgs = []

    for reward, count in rewards.items():
        if reward.startswith("A shark emote") and count > 1:
            reward = reward.replace("A", "").replace("emote", "emotes")
        elif reward.startswith("A shark emote"):
            reward = reward.replace("A", "")
        elif reward.startswith("Custom art") and count > 1:
            reward = reward.replace("art", "arts")
        elif reward.startswith("Date night") and count > 1:
            reward = reward.replace("night", "nights").replace("a 4 hour session", "4 hour sessions")
        msgs.append(f"{count}{f'{reward}' if reward[0] == ' ' else f' {reward}'}")
    msg = ", ".join(msgs)

    print(f"rewards msg: {msg} \n")


# get_rewards(0, 200)

# get_rewards(40, 120)

# get_rewards(0, 90)

# get_rewards(120, 400)

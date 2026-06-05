import asyncio  # noqa
import random  # noqa
import os
from datetime import datetime
import subprocess
import sys

from dotenv import load_dotenv  # noqa
import shutil
from twitchAPI.chat import Chat, ChatCommand, ChatMessage, EventData  # noqa
from twitchAPI.oauth import UserAuthenticator  # noqa
from twitchAPI.twitch import Twitch  # noqa
from twitchAPI.type import AuthScope, ChatEvent  # noqa

from shark_catch import get_sharkpct, get_missing_shark_names, feed_sharks, compute_mood, choose_shark_for_catch
from shark_db_interaction import get_feed_info, reward_coins, catch_shark, is_daily_catch_done
from utils.core import get_full_path

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
TARGET_CHANNELs = ["spiderbyte2007", "sharkocalypse"]
assert CLIENT_ID, "Client ID is none, check if ENV exists"
assert CLIENT_SECRET, "Client Secret is None, check if ENV exists"

FEED_LINES = [
    "you scatter fresh chum across the surface",
    "you toss a bucket of fish into the water",
    "you toss some pelicans into the water for the sharks to feed",
]
TARGET_CHANNEL = ["sharkocalypse", "dyslexxik"]


class SharkBot:
    def __init__(self, app_id: str, app_secret: str, user_scope: list[AuthScope], target_channels: list[str]):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_scope = user_scope
        self.target_channels = target_channels

        self.eventsub_shark: EventSubWebsocket | None = None
        self.eventsub_dys: EventSubWebsocket | None = None
        self.twitch: Twitch | None = None
        self.chat: Chat | None = None

    async def setup(self):
        self.sharkocalypse_twitch = await Twitch(self.app_id, self.app_secret)
        redeem_helper = UserAuthenticationStorageHelper(
            self.sharkocalypse_twitch, USER_SCOPE, Path("tokens/sharkocalypse.json")
        )
        await redeem_helper.bind()

        self.dyslexxik_twitch = await Twitch(self.app_id, self.app_secret)
        dys_redeem_helper = UserAuthenticationStorageHelper(self.dyslexxik_twitch, USER_SCOPE, Path("tokens/dyslexxik.json"))
        await dys_redeem_helper.bind()

        # for sharkocalypse
        user = await first(self.sharkocalypse_twitch.get_users(logins=["sharkocalypse"]))
        if user is None:
            raise ValueError("Could not find user: sharkocalypse. Please check for name change.")
        self.sharkocalypse_id = user.id

        # for dyslexxik
        user_2 = await first(self.sharkocalypse_twitch.get_users(logins=["dyslexxik"]))
        if user_2 is None:
            raise ValueError("Could not find user: dyslexxik. Please check for name change.")
        self.dyslexxik_id = user_2.id

        # for bot
        user_3 = await first(self.sharkocalypse_twitch.get_users(logins=["sharkxxbot"]))
        if user_3 is None:
            raise ValueError("Could not find user: sharkxxbot. Please check for a name change.")
        self.bot_id = user_3.id

        self.eventsub_shark = EventSubWebsocket(self.sharkocalypse_twitch)
        self.eventsub_shark.start()
        print(self.sharkocalypse_id)
        await asyncio.sleep(2)  # give the websocket time to handshake
        print("handshake done")
        await self.eventsub_shark.listen_channel_points_custom_reward_redemption_add(
            broadcaster_user_id=self.sharkocalypse_id, callback=self.on_redemption
        )

        self.eventsub_dys = EventSubWebsocket(self.dyslexxik_twitch)
        self.eventsub_dys.start()
        await self.eventsub_dys.listen_channel_points_custom_reward_redemption_add(
            broadcaster_user_id=self.dyslexxik_id, callback=self.on_redemption
        )

        # Non-redeem section
        self.twitch = await Twitch(self.app_id, self.app_secret)
        auth = UserAuthenticator(self.twitch, self.user_scope)
        authentication = await auth.authenticate()
        assert authentication is not None
        token, refresh_token = authentication
        await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)

        self.chat = await Chat(self.twitch)

    async def on_message(self, msg: ChatMessage):
        assert msg.room
        print(f"in {msg.room.name}, {msg.user.name} said: {msg.text}")

    async def on_ready(self, ready_event: EventData):
        print("Bot is ready for work, joining channels")
        # join our target channel, if you want to join multiple, either call join for each individually
        # or even better pass a list of channels as the argument
        await ready_event.chat.join_room(self.target_channels)
        # you can do other bot initialization things in here
        print("Bot has joined the channels")

    async def sharkpct(self, cmd: ChatCommand):
        assert cmd.room
        user = cmd.user
        name = user.display_name
        twitch_id = user.id
        percentage, total_sharks, total_caught = await get_sharkpct(int(twitch_id))
        if percentage == 100.0:
            await cmd.reply(f"🎉 {name}, you've completed the SharkDex: 100% ({total_caught} / {total_sharks})")
            return

        missing = await get_missing_shark_names(int(twitch_id))
        body_2 = None
        if missing:
            body = f"{percentage:.1f}% complete ({total_caught} / {total_sharks}). Missing the following: "
            for shark in missing:
                if len(body + shark + ", ") <= 500:
                    body += shark + ", "
                else:
                    body_2 = "You've got more sharks missing"
                    break
        else:
            body = f"{percentage:.1f}% complete ({total_caught} / {total_sharks})."

        await cmd.reply(body)
        if body_2:
            await cmd.reply(body_2)

    async def feed(self, cmd: ChatCommand):
        assert cmd.room
        user = cmd.user
        name = user.display_name
        twitch_id = user.id
        info = await feed_sharks(int(twitch_id))
        if not info:
            await cmd.reply(
                f"{name}, I could not feed your sharks. You didn't link your twitch or you didn't do the tutorial on discord"
            )
            return

        mood = info[0]
        early_msg = info[1]
        extra = info[2]

        if mood is None:
            await cmd.reply(f"{name}, mood is somehow none, contact spiderbyte2007 and tell him what happened.")
            return

        face = EMOJI_MOOD[mood]
        feed_info = await get_feed_info(int(twitch_id))
        if not feed_info:
            streak = 0
        else:
            _, streak = feed_info

        throw_line = random.choice(FEED_LINES)

        if early_msg:
            await cmd.reply(
                f"🍽️ {name}, you already fed this stream. Current mood: {face} {mood.capitalize()} (streak: {streak})"
            )
            return
        else:
            await cmd.reply(f"🪣 {name}, {throw_line}. Mood now: {face} {mood.capitalize()} (streak: {streak}). {extra}")

    async def sharkstatus(self, cmd: ChatCommand):
        user = cmd.user
        name = user.name
        twitch_id = user.id
        feed_info = await get_feed_info(int(twitch_id))
        if not feed_info:
            await cmd.reply(
                f"{name}, I could not check on your sharks. "
                "You didn't link your twitch or you didn't do the tutorial on discord"
            )
            return
        last_fed, streak = feed_info
        mood = await compute_mood(last_fed, streak)
        face = EMOJI_MOOD[mood]
        when = "never" if not last_fed else last_fed
        delta = (datetime.now().date() - datetime.strptime(last_fed, r"%Y-%m-%d").date()).days if last_fed else 99999
        if delta >= 2:
            tail = f" (last fed {delta} days ago!)"
        elif delta == 1:
            tail = " (fed yesterday)"
        else:
            tail = " (fed today)"

        await cmd.reply(f"🧪 {name}'s tank — Mood: {face} {mood.capitalize()} | Feed streak: {streak} | Last fed: {when}{tail}")

    async def catchshark(self, cmd: ChatCommand):
        user = cmd.user
        name = user.name
        twitch_id = user.id
        if await is_daily_catch_done(int(twitch_id)):
            await cmd.reply(f"{name} You have already caught your shark for the day!")
            return

        shark_caught, rarity = await choose_shark_for_catch()
        coins_earned = await reward_coins(int(twitch_id), rarity, shark_caught)
        caught = await catch_shark(int(twitch_id), name, datetime.now(), shark_caught, rarity)
        if caught:
            await cmd.reply(
                f"Congratulations {name}, you have caught a {rarity} {shark_caught} and earned {coins_earned} coins."
            )
        else:
            await cmd.reply(f"{name}, I could not find your dex, did you link your twitch or do the tutorial on discord?")

    async def shark_tooth(self, cmd: ChatCommand):
        user = cmd.user
        name = user.name
        twitch_id = user.id
        # Wait for further instructions

    async def restart(self, cmd: ChatCommand):
        if cmd.user.name != "spiderbyte2007":
            await cmd.reply("Only spider can command me to restart")
            return

        os.environ["PATH"] = get_full_path()
        git_path = shutil.which("git")
        try:
            if not git_path:
                await cmd.reply("Cannot find git, try again later")
                return
            subprocess.run([git_path, "pull"])
            await cmd.reply("Pulled successfully")
            subprocess.run([sys.executable, "setup.py"])
            await cmd.reply("Successfully installed all dependencies")
        except subprocess.CalledProcessError as e:
            await cmd.reply(f"Failed, error: {e.stderr}")
        except Exception as e:
            await cmd.reply(f"Failed: Error {str(e)}")

        await cmd.send("Restarting now...")

        subprocess.Popen([sys.executable] + sys.argv)
        await self.close_bot()

    async def close_bot(self):
        assert self.chat, "chat is None"
        assert self.twitch, "twitch is None"
        self.chat.stop()
        await self.twitch.close()

    async def run(self):
        await self.setup()
        # Making sure everything was set up properly
        assert self.chat, "chat is still None"
        assert self.twitch, "twitch is still None"
        assert self.eventsub_dys, "eventsub for dys is still None"
        assert self.eventsub_shark, "event sub for shark is still None"
        assert self.dyslexxik_id, "dys's ID is still None"
        assert self.sharkocalypse_id, "shark's ID is still None"
        assert self.bot_id, "Bot's ID is still None"

        # listen to when the bot is done starting up and ready to join channels
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        # listen to chat messages
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        # listen to commands
        self.chat.register_command("sharkpct", self.sharkpct)
        self.chat.register_command("shark%", self.sharkpct)

        self.chat.register_command("feed", self.feed)

        self.chat.register_command("sharkstatus", self.sharkstatus)
        self.chat.register_command("tank", self.sharkstatus)
        self.chat.register_command("mood", self.sharkstatus)

        self.chat.register_command("catchshark", self.catchshark)
        self.chat.register_command("sharkcatch", self.catchshark)

        self.chat.register_command("restart", self.restart)

        # we are done with our setup, lets start this bot up!
        self.chat.start()

        # lets run till we press enter in the console
        try:
            input("press ENTER to stop \n")
        finally:
            # now we can close the chat bot and the twitch api client
            await self.eventsub_dys.stop()
            await self.eventsub_shark.stop()
            self.chat.stop()
            await self.twitch.close()


assert APP_ID
assert APP_SECRET

bot = SharkBot(APP_ID, APP_SECRET, USER_SCOPE, TARGET_CHANNEL)
asyncio.run(bot.run())

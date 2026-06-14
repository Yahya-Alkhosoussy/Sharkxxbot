import asyncio
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv
from twitchAPI.chat import Chat, ChatCommand, ChatMessage, EventData
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticationStorageHelper, UserAuthenticator
from twitchAPI.object.eventsub import (
    ChannelBanEvent,
    ChannelPointsCustomRewardRedemptionAddEvent,
    ChannelRaidEvent,
    ChannelUnbanEvent,
)
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent

from custom_commands import check_for_command as is_command_existing
from mod_action import add_ban, get_banned_users, remove_ban  # noqa
from quotes import get_quote
from redeems.redeems import deal_with_sharktooth, deal_with_VIP
from utils.core import get_full_path

load_dotenv()

APP_ID = os.getenv("client_id")
APP_SECRET = os.getenv("client_secret")
MOD_SCOPE = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.MODERATOR_READ_BANNED_USERS,
    AuthScope.MODERATOR_MANAGE_BANNED_USERS,
    AuthScope.MODERATOR_READ_UNBAN_REQUESTS,
    AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS,
    AuthScope.MODERATOR_READ_VIPS,
]
BROADCAST_SCOPE = [AuthScope.CHANNEL_READ_REDEMPTIONS]
USER_SCOPE = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.USER_WRITE_CHAT,
    AuthScope.CHANNEL_READ_REDEMPTIONS,
    AuthScope.MODERATOR_READ_BANNED_USERS,
    AuthScope.MODERATOR_MANAGE_BANNED_USERS,
    AuthScope.MODERATOR_READ_UNBAN_REQUESTS,
    AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS,
    AuthScope.MODERATOR_READ_VIPS,
]
TARGET_CHANNEL = ["sharkocalypse", "dyslexxik", "spiderbyte2007"]


class SharkBot:
    def __init__(self, app_id: str, app_secret: str, user_scope: list[AuthScope], target_channels: list[str]):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_scope = user_scope
        self.target_channels = target_channels

        self.eventsub_shark: EventSubWebsocket | None = None
        self.eventsub_dys: EventSubWebsocket | None = None
        self.mod_eventsub_shark: EventSubWebsocket | None = None
        self.mod_eventsub_dys: EventSubWebsocket | None = None
        self.twitch: Twitch | None = None
        self.chat: Chat | None = None
        self.sharkocalypse_twitch: Twitch | None = None
        self.sharkocalypse_redeem_twitch: Twitch | None = None
        self.sharkocalypse_id: str | None = None
        self.dyslexxik_twitch: Twitch | None = None
        self.dyslexxik_redeem_twitch: Twitch | None = None
        self.dyslexxik_id: str | None = None
        self.bot_id: str | None = None

    async def setup(self):
        self.sharkocalypse_twitch = await Twitch(self.app_id, self.app_secret)
        shark_twitch_helper = UserAuthenticationStorageHelper(
            self.sharkocalypse_twitch, MOD_SCOPE, Path("tokens/sharkocalypse_mod.json")
        )
        await shark_twitch_helper.bind()

        self.sharkocalypse_redeem_twitch = await Twitch(self.app_id, self.app_secret)
        shark_redeem_helper = UserAuthenticationStorageHelper(
            self.sharkocalypse_redeem_twitch, BROADCAST_SCOPE, Path("tokens/sharkocalypse_broadcast.json")
        )
        await shark_redeem_helper.bind()
        token = self.sharkocalypse_redeem_twitch.get_user_auth_token()

        self.dyslexxik_twitch = await Twitch(self.app_id, self.app_secret)
        dys_twitch_helper = UserAuthenticationStorageHelper(self.dyslexxik_twitch, MOD_SCOPE, Path("tokens/dyslexxik_mod.json"))
        await dys_twitch_helper.bind()

        self.dyslexxik_redeem_twitch = await Twitch(self.app_id, self.app_secret)
        dys_redeem_helper = UserAuthenticationStorageHelper(
            self.dyslexxik_redeem_twitch, BROADCAST_SCOPE, Path("tokens/dyslexxik_broadcast.json")
        )
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

        self.eventsub_shark = EventSubWebsocket(self.sharkocalypse_redeem_twitch)
        self.eventsub_shark.start()
        print(self.sharkocalypse_id)

        await self.eventsub_shark.listen_channel_points_custom_reward_redemption_add(
            broadcaster_user_id=self.sharkocalypse_id, callback=self.on_redemption
        )

        self.eventsub_dys = EventSubWebsocket(self.dyslexxik_redeem_twitch)
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

        self.mod_eventsub_shark: EventSubWebsocket | None = EventSubWebsocket(self.sharkocalypse_twitch)
        self.mod_eventsub_shark.start()

        self.mod_eventsub_dys: EventSubWebsocket | None = EventSubWebsocket(self.dyslexxik_twitch)
        self.mod_eventsub_dys.start()

        self.chat = await Chat(self.twitch)

    async def refresh_bans(self):
        assert self.twitch
        assert self.dyslexxik_id
        assert self.sharkocalypse_id

        shark_banned_users = [user async for user in self.twitch.get_banned_users(self.sharkocalypse_id)]
        dys_banned_users = [user async for user in self.twitch.get_banned_users(self.dyslexxik_id)]

        for banned_user in shark_banned_users:
            await add_ban(
                streamer="sharkocalypse",
                banned_user=banned_user.user_name,
                banned_user_id=int(banned_user.user_id),
                reason=banned_user.reason,
                mod_that_banned_them=banned_user.moderator_name,
                when_banned=banned_user.created_at,
            )

        for _banned_user in dys_banned_users:
            await add_ban(
                streamer="dyslexxik",
                banned_user=_banned_user.user_name,
                banned_user_id=int(_banned_user.user_id),
                reason=_banned_user.reason,
                mod_that_banned_them=_banned_user.moderator_name,
                when_banned=_banned_user.created_at,
            )

    async def on_ready(self, ready_event: EventData):
        print("Bot is ready for work, joining channels")
        # join our target channel, if you want to join multiple, either call join for each individually
        # or even better pass a list of channels as the argument
        await ready_event.chat.join_room(TARGET_CHANNEL)
        # you can do other bot initialization things in here
        print("Bot has joined the channels")

    # happens upon a redeem
    async def on_redemption(self, _event: ChannelPointsCustomRewardRedemptionAddEvent):
        assert self.twitch
        assert self.bot_id
        event = _event.event
        reward = event.reward
        twitch_name: str = event.user_name
        twitch_id: int = int(event.user_id)
        if reward.title == "daily shark tooth!":
            crystal = await deal_with_sharktooth(twitch_name, twitch_id)
            await self.twitch.send_chat_message(
                broadcaster_id=event.broadcaster_user_id,
                sender_id=self.bot_id,
                message=f"@{twitch_name} you've redeemed shark tooth and got {crystal}!!",
            )
        elif reward.title == "VIP":
            await deal_with_VIP(twitch_name, twitch_id)

    # happens upon a message being sent
    async def on_message(self, msg: ChatMessage):
        assert msg.room
        print(f"in {msg.room.name}, {msg.user.name} said: {msg.text}")
        reply = await is_command_existing(msg.text, msg.room.name)
        if reply and isinstance(reply, str):
            await msg.reply(reply)

    # this will be called whenever someone subscribes to a channel
    # async def on_sub(sub: ChatSub):
    #     assert sub.room
    #     print(f"New subscription in {sub.room.name}: \n  Type: {sub.sub_plan} \n  Message: {sub.sub_message}")

    async def on_raid(self, _event: ChannelRaidEvent):
        assert self.twitch
        assert self.chat

        event = _event.event
        raider_name = event.from_broadcaster_user_name
        raider_id = event.from_broadcaster_user_id
        channel_raided = event.to_broadcaster_user_name
        viewer_count = event.viewers

        stream = await first(self.twitch.get_streams(user_id=[raider_id]))

        if stream:
            game = stream.game_name
        else:
            channel_info = await self.twitch.get_channel_information(broadcaster_id=raider_id)
            game = channel_info[0].game_name

        await self.chat.send_message(
            room=channel_raided,
            text=f"{raider_name} is raiding the cult from the realm of {game} with {viewer_count} others."
            f"Wanna check out their rituals? https://twitch.tv/{raider_name}",
        )

    async def quote_command(self, cmd: ChatCommand):
        assert cmd.room
        quote = await get_quote()
        if quote is None:
            await cmd.reply("I don't have any quotes to give :(")
        else:
            await cmd.reply(f"Here's a quote: {quote}")

    async def braincells_command(self, cmd: ChatCommand):
        assert cmd.room
        count = random.randint(0, 100)
        await cmd.reply(f"You have {count} braincells")

    async def sharkfact_command(self, cmd: ChatCommand):
        file_path = Path(__file__)
        database = file_path.parent.parent / "Shark-Bot" / "databases" / "shark_game.db"
        async with aiosqlite.connect(database) as conn:
            async with conn.execute("SELECT name, fact FROM sharks") as cur:
                results = await cur.fetchall()
                facts: dict = {}  # shark name -> fact
                shark_names = []
                for result in results:
                    facts[result[0]] = {result[1]}
                    shark_names.append(result[0])
                how_many = len(shark_names)
                index = random.randint(0, how_many)
                name = shark_names[index]
                await cmd.reply(f"Your random shark fact is for {name} and it is {facts[name]}")

    async def on_ban(self, banEvent: ChannelBanEvent):
        assert self.dyslexxik_twitch
        assert self.sharkocalypse_twitch
        assert self.bot_id
        assert self.dyslexxik_id
        assert self.sharkocalypse_id

        event = banEvent.event
        streamer = event.broadcaster_user_name

        if event.ends_at is not None:
            return

        await add_ban(
            streamer=streamer,
            banned_user=event.user_name,
            banned_user_id=int(event.user_id),
            reason=event.reason,
            mod_that_banned_them=event.moderator_user_name,
            when_banned=event.banned_at,
        )
        if streamer == "sharkocalypse":
            await self.dyslexxik_twitch.ban_user(
                broadcaster_id=self.dyslexxik_id,
                moderator_id=self.bot_id,
                user_id=event.user_id,
                reason=event.reason,
            )
        elif streamer == "dyslexxik":
            await self.sharkocalypse_twitch.ban_user(
                broadcaster_id=self.sharkocalypse_id,
                moderator_id=self.bot_id,
                user_id=event.user_id,
                reason=event.reason,
            )

    async def on_unban(self, unbanEvent: ChannelUnbanEvent):
        assert self.dyslexxik_id
        assert self.sharkocalypse_id
        assert self.bot_id
        assert self.dyslexxik_twitch
        assert self.sharkocalypse_twitch

        event = unbanEvent.event
        streamer = event.broadcaster_user_name
        await remove_ban(streamer, event.user_name)
        if streamer == "dyslexxik":
            await self.sharkocalypse_twitch.unban_user(
                broadcaster_id=self.sharkocalypse_id,
                moderator_id=self.bot_id,
                user_id=event.user_id,
            )
        elif streamer == "sharkocalypse":
            await self.dyslexxik_twitch.unban_user(
                broadcaster_id=self.dyslexxik_id,
                moderator_id=self.bot_id,
                user_id=event.user_id,
            )

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
            subprocess.run([git_path, "pull"], check=True)
            await cmd.send("Pulled successfully")
            subprocess.run([sys.executable, "setup.py"], check=True)
            await cmd.send("Successfully installed all dependencies")
        except subprocess.CalledProcessError as e:
            await cmd.send(f"Failed, error: {e.stderr}")
        except Exception as e:
            await cmd.send(f"Failed: Error {str(e)}")

        await cmd.send("Restarting now...")
        await self.close_bot()
        subprocess.Popen([sys.executable] + sys.argv)
        asyncio.get_event_loop().stop()

    async def close_bot(self):
        assert self.eventsub_dys
        assert self.eventsub_shark
        assert self.mod_eventsub_dys
        assert self.mod_eventsub_shark
        assert self.chat
        assert self.twitch
        # now we can close the chat bot and the twitch api client
        await self.eventsub_dys.stop()
        await self.eventsub_shark.stop()
        await self.mod_eventsub_dys.stop()
        await self.mod_eventsub_shark.stop()
        try:
            await asyncio.wait_for(asyncio.to_thread(self.chat.stop), timeout=3.0)
        except asyncio.TimeoutError:
            pass  # force restart after 3 seconds

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
        assert self.mod_eventsub_shark, "Shark's mod event sub is not set up properly"
        assert self.mod_eventsub_dys, "Dys's mod event sub is not set up properly"

        # listen to when the bot is done starting up and ready to join channels
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        # listen to chat messages
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        # # listen to channel subscriptions
        # chat.register_event(ChatEvent.SUB, on_sub)
        # listen to a raid
        await self.eventsub_shark.listen_channel_raid(self.on_raid)
        await self.eventsub_dys.listen_channel_raid(self.on_raid)
        self.chat.register_command("quote", self.quote_command)
        self.chat.register_command("sharkfact", self.sharkfact_command)
        self.chat.register_command("restart", self.restart)

        # print(self.mod_eventsub_shark._twitch._user_auth_token)
        # print(self.mod_eventsub_shark._twitch._user_auth_scope)

        await self.mod_eventsub_shark.listen_channel_ban(broadcaster_user_id=self.sharkocalypse_id, callback=self.on_ban)
        await self.mod_eventsub_shark.listen_channel_unban(broadcaster_user_id=self.sharkocalypse_id, callback=self.on_unban)
        await self.mod_eventsub_dys.listen_channel_ban(broadcaster_user_id=self.dyslexxik_id, callback=self.on_ban)
        await self.mod_eventsub_dys.listen_channel_unban(broadcaster_user_id=self.dyslexxik_id, callback=self.on_unban)

        # we are done with our setup, lets start this bot up!
        self.chat.start()

        # lets run till we press enter in the console
        try:
            input("press ENTER to stop \n")
        finally:
            await self.close_bot()


assert APP_ID
assert APP_SECRET

bot = SharkBot(APP_ID, APP_SECRET, USER_SCOPE, TARGET_CHANNEL)
asyncio.run(bot.run())

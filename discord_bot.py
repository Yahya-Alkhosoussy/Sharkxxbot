import discord
from discord.ext import commands

from utils.core import GiftedSub


class DiscordBot(commands.Bot):
    def __init__(self, token: str | None):
        if token is None:
            raise ValueError("Token is None")
        self.token = token

    async def on_ready(self):
        assert self.user is not None
        self.gifted_cog = GiftedCog(self)
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message):
        await self.process_commands(message)


class GiftedCog:
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.reciepts_channel = self.bot.get_channel(1505513311024840864)
        self.guild = self.bot.get_guild(1273776575266951268)

    async def send_gifted_notice(self, message: GiftedSub):
        try:
            assert isinstance(self.reciepts_channel, discord.TextChannel)
            assert self.guild
            assert
        except AssertionError as e:
            print(f"Got an error: {e}")
            return

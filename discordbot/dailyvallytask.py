import datetime
import random

import discord
from discord.ext import tasks, commands

from discordbot.constants import VALORANT_CHAT, VALORANT_ROLE, BSE_SERVER_ID


class AfterWorkVally(commands.Cog):
    def __init__(self, bot: discord.Client, guilds, logger):
        self.bot = bot
        self.logger = logger
        self.guilds = guilds
        self.vally_message.start()

        self.messages = [
            "Anyone playing after-work {role} today?",
            "Who's about for {role} today?",
            "Anyone wanna get salty playing {role} today?"
        ]

    def cog_unload(self):
        """
        Method for cancelling the loop.
        :return:
        """
        self.vally_message.cancel()

    @tasks.loop(minutes=10)
    async def vally_message(self):
        """
        Loop that makes sure the King is assigned correctly
        :return:
        """
        now = datetime.datetime.now()

        if now.weekday() not in [0, 1, 2, 3, 4]:
            return

        if now.hour != 15 or not (45 <= now.minute <= 54):
            return

        print(f"Time to send vally message!")

        if BSE_SERVER_ID not in self.guilds:
            return

        guild = await self.bot.fetch_guild(BSE_SERVER_ID)  # type: discord.Guild
        channel = await guild.fetch_channel(VALORANT_CHAT)
        role = guild.get_role(VALORANT_ROLE)

        message = random.choice(self.messages)  # type: str
        message = message.format(role=role.mention)

        print(f"Sending daily vally message: {message}")
        await channel.send(content=message)

    @vally_message.before_loop
    async def before_vally_message(self):
        """
        Make sure that websocket is open before we starting querying via it.
        :return:
        """
        await self.bot.wait_until_ready()

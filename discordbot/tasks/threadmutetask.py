import datetime

import discord
from discord.ext import tasks, commands

from discordbot.constants import BSE_SERVER_ID, GENERAL_CHAT
from mongo.bsedataclasses import SpoilerThreads


class ThreadSpoilerTask(commands.Cog):
    def __init__(self, bot: discord.Client, guilds, logger):
        self.bot = bot
        self.logger = logger
        self.guilds = guilds
        self.spoilers = SpoilerThreads()

        self.thread_mute.start()

    def cog_unload(self):
        """
        Method for cancelling the loop.
        :return:
        """
        self.thread_mute.cancel()

    @tasks.loop(minutes=15)
    async def thread_mute(self):
        """
        Loop that makes sure the King is assigned correctly
        :return:
        """
        now = datetime.datetime.now()
        if now.hour != 8 or not (0 <= now.minute < 15):
            return

        if BSE_SERVER_ID not in self.guilds:
            return

        self.logger.info("Checking spoiler threads for mute messages")
        guild = self.bot.get_guild(BSE_SERVER_ID)
        general = await guild.fetch_channel(GENERAL_CHAT)
        threads = general.threads

        if not threads:
            self.logger.info("Found no threads to parse")
            # no threads
            return

        for thread in general.threads:
            self.logger.info(f"Checking {thread.name} for spoiler message")
            if "spoiler" not in thread.name.lower():
                self.logger.info("Thread doesn't have spoiler name")
                continue

            thread_id = thread.id
            thread_info = self.spoilers.get_thread_by_id(BSE_SERVER_ID, thread_id)

            if not thread_info:
                self.logger.info(f"No info for thread {thread_id}, {thread.name}")
                continue

            if not thread_info["active"]:
                # thread is no longer active
                self.logger.info("Thread is no longer active")
                continue

            day = thread_info["day"]
            if now.weekday() != day:
                self.logger.info(f"Not the right day for {thread.name}: our day: {now.weekday()}, required: {day}")
                # not the right day for this spoiler thread
                continue

            message = "New episode today - remember to mute cuties @everyone xoxo"
            await thread.send(content=message, allowed_mentions=discord.AllowedMentions(everyone=True))
            self.logger.info(f"Sent message to {thread.id}, {thread.name}: {message}")

    @thread_mute.before_loop
    async def before_thread_mute(self):
        """
        Make sure that websocket is open before we starting querying via it.
        :return:
        """
        await self.bot.wait_until_ready()

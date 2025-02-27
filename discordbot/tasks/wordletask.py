import datetime
import random

import discord
from discord.ext import tasks, commands

from discordbot.constants import BSE_SERVER_ID, GENERAL_CHAT
from discordbot.wordle.wordlesolver import WordleSolver
from mongo.bsedataclasses import WordleAttempts


class WordleTask(commands.Cog):
    def __init__(self, bot: discord.Client, guilds, logger):
        self.bot = bot
        self.logger = logger
        self.guilds = guilds
        self.wordle_message.start()
        self.wordles = WordleAttempts()
        self.set_wordle_activity = False
        self.sent_wordle = False
        self.wait_iters = None

    def cog_unload(self):
        """
        Method for cancelling the loop.
        :return:
        """
        self.wordle_message.cancel()

    @tasks.loop(minutes=10)
    async def wordle_message(self):
        """
        Loop that makes sure the King is assigned correctly
        :return:
        """
        now = datetime.datetime.now()

        if now.hour < 8:
            self.wait_iters = None
            self.sent_wordle = False
            self.set_wordle_activity = False
            return

        if self.sent_wordle and not self.set_wordle_activity:
            return

        if now.hour >= 10:
            if self.set_wordle_activity:
                self.logger.info("Setting activity back to default")
                listening_activity = discord.Activity(
                    name="conversations",
                    state="Listening",
                    type=discord.ActivityType.listening,
                    details="Waiting for commands!"
                )
                await self.bot.change_presence(activity=listening_activity, status=discord.Status.online)
                self.set_wordle_activity = False

            return

        if self.sent_wordle:
            return

        if not self.set_wordle_activity:
            self.logger.info("Setting wordle activity")
            game = discord.Game("Wordle")
            await self.bot.change_presence(status=discord.Status.online, activity=game)
            self.set_wordle_activity = True

        if self.wait_iters is None:
            self.wait_iters = random.randint(0, 5)
            self.logger.info(f"Setting iterations to {self.wait_iters}")
            return

        if self.wait_iters != 0:
            self.logger.info("Decrementing countdown...")
            self.wait_iters -= 1
            return

        # wait iters is 0
        assert self.wait_iters == 0

        # actually do wordle now

        wordle_solver = WordleSolver(self.logger)
        await wordle_solver.get_driver()

        self.logger.debug("Solving wordle...")
        solved_wordle = await wordle_solver.solve()

        attempts = 1
        while not solved_wordle.solved and attempts < 5:
            # if we fail - try again as there's some randomness to it
            self.logger.debug(f"Failed wordle - attempting again: {attempts}")
            wordle_solver = WordleSolver(self.logger)
            await wordle_solver.get_driver()
            solved_wordle = await wordle_solver.solve()
            attempts += 1

        # put it into dark mode
        message = solved_wordle.share_text.replace("⬜", "⬛")
        spoiler_message = (
            f"Solved wordle in `{solved_wordle.guess_count}`, "
            f"word was: || {solved_wordle.actual_word} ||"
        )

        guild = await self.bot.fetch_guild(BSE_SERVER_ID)
        channel = await guild.fetch_channel(GENERAL_CHAT)

        self.logger.info(f"Sending wordle message: {message}")
        sent_message = await channel.send(content=message)
        if solved_wordle.solved:
            await sent_message.reply(content=spoiler_message)

        self.wordles.document_wordle(BSE_SERVER_ID, solved_wordle)

        self.sent_wordle = True

        self.logger.info("Setting activity back to default")
        listening_activity = discord.Activity(
            name="conversations",
            state="Listening",
            type=discord.ActivityType.listening,
            details="Waiting for commands!"
        )
        await self.bot.change_presence(activity=listening_activity, status=discord.Status.online)
        self.set_wordle_activity = False

    @wordle_message.before_loop
    async def before_wordle_message(self):
        """
        Make sure that websocket is open before we starting querying via it.
        :return:
        """
        await self.bot.wait_until_ready()

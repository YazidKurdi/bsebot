import datetime
import math
import random

import discord
from discord.ext import tasks, commands

from apis.giphyapi import GiphyAPI
from discordbot.bot_enums import TransactionTypes
from discordbot.constants import BSEDDIES_KING_ROLES, BSEDDIES_REVOLUTION_CHANNEL
from discordbot.embedmanager import EmbedManager
from discordbot.views import RevolutionView
from mongo.bsepoints import UserPoints
from mongo.bseticketedevents import RevolutionEvent
from mongo.datatypes import RevolutionEvent as RevolutionEventType


class BSEddiesRevolutionTask(commands.Cog):
    def __init__(self, bot: discord.Client, guilds, logger, giphy_token):
        self.bot = bot
        self.user_points = UserPoints()
        self.revolutions = RevolutionEvent()
        self.embed_manager = EmbedManager(logger)
        self.logger = logger
        self.guilds = guilds
        self.giphy_api = GiphyAPI(giphy_token)
        self.rev_started = False
        self.revolution.start()

        for guild_id in guilds:
            if _ := self.revolutions.get_open_events(guild_id):
                self.rev_started = True

    def cog_unload(self):
        """
        Method for cancelling the loop.
        :return:
        """
        self.revolution.cancel()

    @tasks.loop(minutes=1)
    async def revolution(self):
        """
        Constantly checks to make sure that all events have been closed properly or raised correctly
        :return:
        """
        now = datetime.datetime.now()

        if not self.rev_started and (now.weekday() != 6 or now.hour != 16 or now.minute != 0):
            return

        for guild_id in self.guilds:

            king_user = self.user_points.get_current_king(guild_id)

            user_points = king_user["points"]

            if not self.rev_started:
                event = self.revolutions.create_event(
                    guild_id,
                    datetime.datetime.now(),
                    datetime.datetime.now() + datetime.timedelta(hours=3, minutes=30),
                    king_user["uid"],
                    user_points,
                    BSEDDIES_REVOLUTION_CHANNEL
                )
            else:
                event = self.revolutions.get_open_events(guild_id)[0]

            self.rev_started = True

            message = event.get("message_id")
            if message is None:
                await self.create_event(guild_id, event)
                continue

            if now > event["expired"]:
                await self.handle_resolving_bet(guild_id, event)
                self.logger.info("Changing revolution task interval to 30 minutes.")
                continue

            # if (event["expired"] - now).total_seconds() < 10800 and not event.get("three_hours"):
            #    await self.send_excited_gif(guild_id, event, "Three hours", "three_hours")

            # elif now.hour == 17 and now.minute == 30 and not event.get("two_hours"):
            #     await self.send_excited_gif(guild_id, event, "Two hours", "two_hours")

            elif now.hour == 18 and now.minute == 30 and not event.get("one_hour"):
                await self.send_excited_gif(guild_id, event, "One hour", "one_hour")

            # elif now.hour == 19 and now.minute == 0 and not event.get("half_hour"):
            #     await self.send_excited_gif(guild_id, event, "HALF AN HOUR", "half_hour")

            elif now.hour == 19 and now.minute == 15 and not event.get("quarter_house"):
                await self.send_excited_gif(guild_id, event, "15 MINUTES", "quarter_hour")

    async def send_excited_gif(self, guild_id: int, event: RevolutionEventType, hours_string: str, key: str):
        """
        Method for sending a countdown gif in regards to tickets and things
        :param guild_id:
        :param event:
        :param hours_string:
        :param key:
        :return:
        """
        guild_obj = await self.bot.fetch_guild(guild_id)  # type: discord.Guild
        channels = await guild_obj.fetch_channels()
        channel = [c for c in channels if c.id == event.get("channel_id", BSEDDIES_REVOLUTION_CHANNEL)][0]
        gif = await self.giphy_api.random_gif("celebrate")
        await channel.send(
            content=f"Just under **{hours_string.upper()}** to go now - remember to choose your side!️"
        )
        await channel.send(content=gif)
        self.revolutions.update({"_id": event["_id"]}, {"$set": {key: True}})

    async def create_event(self, guild_id: int, event: RevolutionEventType):
        """
        Handle event creation - this takes a DB entry and posts the message into the channel.

        We also set the Channel ID and the Message ID for the
        :param guild_id:
        :param event:
        :return:
        """
        king = self.user_points.get_current_king(guild_id)

        king_user = await self.bot.fetch_user(king["uid"])  # type: discord.User
        guild_obj = await self.bot.fetch_guild(guild_id)  # type: discord.Guild
        role = guild_obj.get_role(BSEDDIES_KING_ROLES[guild_id])  # type: discord.Role
        channels = await guild_obj.fetch_channels()
        channel = [c for c in channels if c.id == event.get("channel_id", BSEDDIES_REVOLUTION_CHANNEL)][0]

        revolution_view = RevolutionView(self.bot, event, self.logger)

        message = self.embed_manager.get_revolution_message(king_user, role, event, guild_obj)
        message_obj = await channel.send(content=message, view=revolution_view)  # type: discord.Message

        self.revolutions.update(
            {"_id": event["_id"]}, {"$set": {"message_id": message_obj.id, "channel_id": message_obj.channel.id}}
        )

        gif = await self.giphy_api.random_gif("revolution")
        await channel.send(content=gif)

    async def handle_resolving_bet(self, guild_id: int, event: RevolutionEventType):
        """
        Method for handling an event that needs resolving.

        We take the event chance and see if we generate a number between 0-100 that's lower than it. If it is, then
        we "win", otherwise we "lose". We handle both those conditions here too.
        :param guild_id:
        :param event:
        :return:
        """
        chance = event["chance"]
        king_id = event.get("king", self.user_points.get_current_king(guild_id)["uid"])
        _users = event["users"]
        revolutionaries = event["revolutionaries"]
        channel_id = event["channel_id"]

        guild_obj = await self.bot.fetch_guild(guild_id)
        channels = await guild_obj.fetch_channels()
        channel = [c for c in channels if c.id == channel_id][0]

        self.rev_started = False

        if len(_users) == 0:
            message = "No-one supported or overthrew the King - nothing happens."
            await channel.send(content=message)
            self.revolutions.close_event(event["event_id"], guild_id, False, 0)
            return

        king_user = await self.bot.fetch_user(king_id)

        val = (random.random() * 100)
        success = val <= chance

        self.logger.debug(f"Number was: {val} and chance was: {chance}")
        points_to_lose = 0

        if not success:
            # revolution FAILED
            message = "Sadly, our revolution has failed. THE KING LIVES :crown: Better luck next week!"

            self.user_points.append_to_transaction_history(
                king_id, guild_id,
                {
                    "type": TransactionTypes.REV_TICKET_KING_WIN,
                    "event_id": event["event_id"],
                    "timestamp": datetime.datetime.now(),
                    "comment": "User survived a REVOLUTION",
                }
            )
            gif = await self.giphy_api.random_gif("disappointed")

        else:
            king_dict = self.user_points.find_user(king_id, guild_id, projection={"points": True})
            points_to_lose = math.floor(event.get('locked_in_eddies', king_dict["points"]) / 2)

            supporters = event["supporters"]

            total_points_to_distribute = points_to_lose
            for supporter in supporters:
                supporter_eddies = self.user_points.get_user_points(supporter, guild_id)
                supporter_eddies_to_lose = math.floor(supporter_eddies * 0.1)
                total_points_to_distribute += supporter_eddies_to_lose
                self.user_points.decrement_points(supporter, guild_id, supporter_eddies_to_lose)
                self.user_points.append_to_transaction_history(
                    supporter, guild_id,
                    {
                        "type": TransactionTypes.SUPPORTER_LOST_REVOLUTION,
                        "amount": supporter_eddies_to_lose * -1,
                        "event_id": event["event_id"],
                        "timestamp": datetime.datetime.now(),
                        "comment": "Supporter lost a revolution",
                    }
                )

            points_each = math.floor(total_points_to_distribute / len(revolutionaries))

            message = (f"SUCCESS! THE KING IS DEAD! We have successfully taken eddies away from the KING. "
                       f"{king_user.mention} will lose **{points_to_lose}** and each of their supporters has lost"
                       f"`10%` of their eddies. Each revolutionary will gain `{points_each}` eddies.")

            self.user_points.decrement_points(king_id, guild_id, points_to_lose)
            self.user_points.append_to_transaction_history(
                king_id, guild_id,
                {
                    "type": TransactionTypes.REV_TICKET_KING_LOSS,
                    "amount": points_to_lose * -1,
                    "event_id": event["event_id"],
                    "timestamp": datetime.datetime.now(),
                    "comment": "King lost a REVOLUTION",
                }
            )

            gif = await self.giphy_api.random_gif("celebrate")

            for user_id in revolutionaries:
                self.user_points.increment_points(user_id, guild_id, points_each)
                self.user_points.append_to_transaction_history(
                    user_id, guild_id,
                    {
                        "type": TransactionTypes.REV_TICKET_WIN,
                        "amount": points_each,
                        "event_id": event["event_id"],
                        "timestamp": datetime.datetime.now(),
                        "comment": "User won a REVOLUTION",
                    }
                )

        await channel.send(content=message)
        await channel.send(content=gif)
        self.revolutions.close_event(event["event_id"], guild_id, success, points_to_lose)

    @revolution.before_loop
    async def before_revolution(self):
        """
        Make sure that websocket is open before we starting querying via it.
        :return:
        """
        await self.bot.wait_until_ready()

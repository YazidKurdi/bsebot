import datetime
import math
import re
from collections import Counter
from typing import List

import discord
from discord.ext import tasks, commands

from discordbot.bot_enums import TransactionTypes
from discordbot.constants import CREATOR, MESSAGE_TYPES, MESSAGE_VALUES, WORDLE_VALUES, HUMAN_MESSAGE_TYPES
from discordbot.constants import GENERAL_CHAT
from mongo.bsedataclasses import TaxRate
from mongo.bsepoints import ServerEmojis, UserPoints, UserInteractions


class EddieGainMessager(commands.Cog):
    """
    Class that exists to send the "You've gained X BSEddies" message.
    The need for this is because we need a task that can send messages.
    This task simply pulls the already calculated data out of the json file that was
    generated by a cronjob and messages the individuals. It only messages them if they have the
    "The Boys" role.
    """
    def __init__(self, bot: discord.Client, guilds, logger):
        self.bot = bot
        self.guilds = guilds
        self.logger = logger
        self.user_points = UserPoints()

        self.eddie_manager = BSEddiesManager(self.bot, self.logger)

        self.eddie_distributer.start()

    def cog_unload(self):
        """
        Stop task method
        :return:
        """
        self.eddie_distributer.cancel()

    @tasks.loop(minutes=1)
    async def eddie_distributer(self):
        """
        Opens up our json file of user IDS and loops over them.
        If the user IDs is in the 'The Boys' group - we message them to tell them of their
        daily BSEddies gain.
        :return:
        """
        now = datetime.datetime.now()

        if now.hour != 7 or now.minute != 30:
            return

        for guild_id in self.guilds:
            eddie_dict = self.eddie_manager.give_out_eddies(guild_id, real=True)

            guild = await self.bot.fetch_guild(guild_id)  # type: discord.Guild

            current_king_id = self.user_points.get_current_king(guild_id)["uid"]

            msg = f"Eddie gain summary:\n"
            for user_id in eddie_dict:

                value = eddie_dict[user_id][0]
                breakdown = eddie_dict[user_id][1]
                tax = eddie_dict[user_id][2]

                if value == 0:
                    continue

                try:
                    user = await guild.fetch_member(int(user_id))  # type: discord.Member
                except discord.NotFound:
                    msg += f"\n- `{user_id}` :  **{value}**"
                    continue

                roles = user.roles  # type: List[discord.Role]

                msg += f"\n- `{user_id}` {user.display_name} :  **{value}**"
                text = f"Your daily salary of BSEDDIES is `{value}` (after tax).\n"

                if user_id == current_king_id:
                    text += f"You gained an additional `{tax}` from tax gains\n"
                else:
                    text += f"You were taxed `{tax}` by the KING.\n"

                text += f"\nThis is based on the following amount of interactivity yesterday:"

                for key in sorted(breakdown):
                    text += f"\n - `{HUMAN_MESSAGE_TYPES[key]}`  :  **{breakdown[key]}**"

                self.logger.info(f"{user.display_name} is gaining `{value} eddies`")

                user_dict = self.user_points.find_user(int(user_id), guild.id)

                if user_dict.get("daily_eddies"):
                    self.logger.info(f"Sending message to {user.display_name} for {value}")
                    try:
                        await user.send(content=text)
                    except discord.Forbidden:
                        continue

            user = await guild.fetch_member(CREATOR)  # type: discord.Member
            try:
                await user.send(content=msg)
            except discord.Forbidden:
                # can't send DM messages to this user
                self.logger.info(f"{user.display_name} - {msg}")

        # next_exec = now.replace(hour=6, minute=0, second=0, microsecond=0).replace(day=now.day + 1)
        # self.eddie_distributer.change_interval(time=next_exec)

    @eddie_distributer.before_loop
    async def before_eddie_distributer(self):
        """
        We want to make sure the websocket is connected before we start sending requests via it
        :return:
        """
        await self.bot.wait_until_ready()


class BSEddiesManager(object):
    """
    Class for managing passive eddie gain.
    """
    def __init__(self, bot: discord.Client, logger):
        self.user_interactions = UserInteractions()
        self.user_points = UserPoints()
        self.server_emojis = ServerEmojis()
        self.tax_rate = TaxRate()
        self.bot = bot
        self.logger = logger

    @staticmethod
    def get_datetime_objects(days=1):
        """
        Get's the datetime START and END of yesterday
        :return:
        """
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=days)
        start = yesterday.replace(hour=0, minute=0, second=0)
        end = yesterday.replace(hour=23, minute=59, second=59)
        return start, end

    def _calc_eddies(self, counter, start=4):
        """
        Quick function to loop over the message types and work out an amount of BSEddies the user will gain
        :param counter:
        :return:
        """
        points = start
        for message_type in MESSAGE_TYPES:
            if val := counter.get(message_type):
                t_points = val * MESSAGE_VALUES[message_type]
                points += t_points
                self.logger.info(f"{t_points} for {message_type}")
        return points

    def calc_individual(
            self,
            user,
            user_dict,
            user_results,
            user_reacted,
            user_reactions,
            start,
            end,
            guild_id,
            real=False
    ):
        """
        Method for calculating the eddie amount of an individual.
        :param user:
        :param user_dict:
        :param user_results:
        :param user_reacted:
        :param user_reactions:
        :param start:
        :param end:
        :param guild_id:
        :param real:
        :return:
        """

        minimum = user_dict.get("daily_minimum", 4)

        if not user_results:
            if minimum == 0:
                return 0, {}

            if minimum < 0:
                if real:
                    self.user_points.set_daily_minimum(user, guild_id, 0)
                return 0, {}

            minimum -= 1
            if real:
                self.user_points.decrement_daily_minimum(user, guild_id, 1)
            if minimum == 0:
                return 0, {}
        else:
            if minimum != 4:
                minimum = 4
                if real:
                    self.user_points.set_daily_minimum(user, guild_id, 4)

        message_types = []
        for r in user_results:
            if isinstance(r["message_type"], list):
                message_types.extend(r["message_type"])
            else:
                message_types.append(r["message_type"])

        # REACTION HANDLING
        for message in user_reacted:
            # messages the user sent that got reacted to
            for reaction in message.get("reactions", []):
                if reaction["user_id"] == user:
                    continue
                if start < reaction["timestamp"] < end:
                    message_types.append("reaction_received")

        for message in user_reactions:
            # messages the user reacted to
            reactions = message.get("reactions", [])

            our_user_reactions = [
                react for react in reactions if react["user_id"] == user and (start < react["timestamp"] < end)
            ]
            for reaction in our_user_reactions:

                if emoji := self.server_emojis.get_emoji_from_name(guild_id, reaction["content"]):
                    message_types.append("custom_emoji_reaction")

                matching_reactions = [
                    react for react in reactions
                    if react["content"] == reaction["content"] and react["user_id"] != user
                ]

                if matching_reactions:
                    # someone else reacted with the same emoji we did
                    _matching = sorted(matching_reactions, key=lambda x: x["timestamp"])
                    if _matching[0]["timestamp"] > reaction["timestamp"]:
                        # we reacted first!
                        for _ in matching_reactions:
                            message_types.append("react_train")

        # add reaction_received events
        for message in user_results:
            if replies := message.get("replies"):
                for reply in replies:
                    if reply["user_id"] == user:
                        continue
                    message_types.append("reply_received")

        count = Counter(message_types)
        eddies_gained = self._calc_eddies(count, minimum)

        eddies_gained = math.floor(eddies_gained)

        count["daily"] = minimum

        return eddies_gained, count

    def give_out_eddies(self, guild_id, real=False, days=1):
        """
        Takes all the user IDs for a server and distributes BSEddies to them
        :param guild_id:
        :param real:
        :param days:
        :return:
        """
        start, end = self.get_datetime_objects(days)

        # query gets all messages yesterday
        results = self.user_interactions.query(
            {
                "guild_id": guild_id,
                "timestamp": {"$gt": start, "$lt": end}
            }
        )

        reactions = self.user_interactions.query(
            {
                "guild_id": guild_id,
                "reactions.timestamp": {"$gt": start, "$lt": end}
             }
        )

        users = self.user_points.get_all_users_for_guild(guild_id)
        users = [u for u in users if not u.get("inactive")]
        user_ids = [u["uid"] for u in users]
        user_dict = {u["uid"]: u for u in users}

        eddie_gain_dict = {}
        wordle_messages = []

        for user in user_ids:
            self.logger.info(f"processing {user}")

            user_results = [r for r in results if r["user_id"] == user]
            user_reacted_messages = [r for r in reactions if r["user_id"] == user]
            user_reactions = [
                r for r in reactions
                if any([react for react in r["reactions"] if react["user_id"] == user])
            ]

            eddies_gained, breakdown = self.calc_individual(
                user,
                user_dict[user],
                user_results,
                user_reacted_messages,
                user_reactions,
                start,
                end,
                guild_id,
                real
            )

            try:
                wordle_message = [w for w in user_results if "wordle" in w["message_type"]][0]
                result = re.search("\d\/\d", wordle_message["content"]).group()
                guesses = result.split("/")[0]

                if guesses != "X":
                    guesses = int(guesses)

                wordle_value = WORDLE_VALUES[guesses]
                eddies_gained += wordle_value

                if "wordle" not in breakdown:
                    breakdown["wordle"] = 3

                breakdown["wordle"] += wordle_value

                if guesses != "X":
                    wordle_messages.append((user, guesses))

            except IndexError as e:
                # just means we had an error with this
                pass

            if eddies_gained == 0:
                continue

            eddie_gain_dict[user] = [eddies_gained, breakdown]

        # grab the bot's wordle message here
        results = self.user_interactions.query(
            {
                "guild_id": guild_id,
                "timestamp": {"$gt": start, "$lt": end},
                "user_id": self.bot.user.id,
                "channel_id": GENERAL_CHAT,
                "message_type": "wordle"
            }
        )

        bot_guesses = 100  # arbitrarily high number
        if results:
            bot_message = results[0]
            bot_result = re.search("\d\/\d", bot_message["content"]).group()
            bot_guesses = bot_result.split("/")[0]
            if bot_guesses != "X":
                bot_guesses = int(bot_guesses)
            else:
                bot_guesses = 100

        # do wordle here
        if wordle_messages:
            wordle_messages = sorted(wordle_messages, key=lambda x: x[1])
            top_guess = wordle_messages[0][1]

            if bot_guesses < top_guess:
                top_guess = bot_guesses

            for wordle_attempt in wordle_messages:
                if wordle_attempt[1] == top_guess:
                    gain_dict = eddie_gain_dict[wordle_attempt[0]][1]
                    gain_dict["wordle_win"] = 1
                    eddie_gain_dict[wordle_attempt[0]] = [eddie_gain_dict[wordle_attempt[0]][0] + 5, gain_dict]

        current_king_id = self.user_points.get_current_king(guild_id)["uid"]
        tax_gains = 0
        
        tax_rate = self.tax_rate.get_tax_rate()
        self.logger.info(f"Tax rate is: {tax_rate}")

        for _user in eddie_gain_dict:
            if _user == "guild":
                continue

            if _user != current_king_id:
                # apply tax
                taxed = math.floor(eddie_gain_dict[_user][0] * tax_rate)
                eddie_gain_dict[_user][0] -= taxed
                eddie_gain_dict[_user].append(taxed)
                tax_gains += taxed

            if real:
                self.logger.info(f"Incrementing {_user} by {eddie_gain_dict[_user][0]}")
                self.user_points.increment_points(_user, guild_id, eddie_gain_dict[_user][0])
                self.user_points.append_to_transaction_history(
                    _user,
                    guild_id,
                    {
                        "type": TransactionTypes.DAILY_SALARY,
                        "amount": eddie_gain_dict[_user][0],
                        "timestamp": datetime.datetime.now(),
                    }
                )
            self.logger.info(f"{_user} gained {eddie_gain_dict[_user][0]}")

        eddie_gain_dict[current_king_id].append(tax_gains)

        if real:
            self.user_points.increment_points(current_king_id, guild_id, eddie_gain_dict[current_king_id][0])
            self.user_points.append_to_transaction_history(
                current_king_id,
                guild_id,
                {
                    "type": TransactionTypes.TAX_GAINS,
                    "amount": eddie_gain_dict[current_king_id][2],
                    "timestamp": datetime.datetime.now(),
                }
            )

        return eddie_gain_dict

"""
File for Slash Command Event Classes

Each class in this file corresponds to a slash command that we've register in commandmanager.CommandManager
These classes handle most of the logic for them
"""

import datetime
import os
import re
from typing import Union

import discord
import xlsxwriter

from discordbot.betmanager import BetManager
from discordbot.bot_enums import TransactionTypes, ActivityTypes
from discordbot.clienteventclasses import BaseEvent
from discordbot.constants import CREATOR, PRIVATE_CHANNEL_IDS, BSEDDIES_KING_ROLES
from discordbot.constants import HUMAN_MESSAGE_TYPES
from discordbot.eddiegains import BSEddiesManager

# views
from discordbot.views import LeaderBoardView, HighScoreBoardView
from discordbot.views import PlaceABetView, CloseABetView, BetView


class BSEddies(BaseEvent):
    """
    A base BSEddies event for any shared methods across
    All slash command classes will inherit from this class
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def _handle_validation(self, ctx: Union[discord.ApplicationContext, discord.Interaction], **kwargs) -> bool:
        """
        Internal method for validating slash command inputs.
        :param ctx: discord ctx to use
        :param kwargs: the additional kwargs to use in validation
        :return: True or False
        """
        if ctx.guild.id not in self.guild_ids:
            return False

        if kwargs.get("admin") and ctx.author.id != CREATOR:
            msg = f"You do not have the permissions to use this command."
            await ctx.respond(content=msg, ephemeral=True)
            return False

        if "friend" in kwargs and (
                isinstance(kwargs["friend"], discord.User) or isinstance(kwargs["friend"], discord.Member)):
            if kwargs["friend"].bot:
                msg = f"Bots cannot be gifted eddies."
                await ctx.respond(content=msg, ephemeral=True)
                return False

            if kwargs["friend"].id == ctx.author.id:
                msg = f"You can't gift yourself points."
                await ctx.respond(content=msg, ephemeral=True)
                return False

        if "amount" in kwargs and isinstance(kwargs["amount"], int):
            if kwargs["amount"] < 0:
                msg = f"You can't _\"gift\"_ someone negative points."
                await ctx.respond(content=msg, ephemeral=True)
                return False

        return True


class BSEddiesView(BSEddies):
    """
    Class for handling `/view` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def view(self, ctx: discord.ApplicationContext):
        """
        Basic view method for handling view slash commands.

        Sends an ephemeral message to the user with their total eddies and any "pending" eddies they
        have tied up in bets.

        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_VIEW)

        ret = self.user_points.find_user(
            ctx.author.id, ctx.guild.id, projection={"points": True, "high_score": True})

        pending = self.user_bets.get_user_pending_points(ctx.author.id, ctx.guild.id)
        msg = (f"You have **{ret['points']}** :money_with_wings:`BSEDDIES`:money_with_wings:!"
               f"\nAdditionally, you have `{pending}` points on 'pending bets'.\n\n"
               f"The _absolute highest_ amount of eddies you've ever had was `{ret.get('high_score', 0)}`!.")
        await ctx.respond(content=msg, ephemeral=True)


class BSEddiesLeaderboard(BSEddies):
    """
    Class for handling `/leaderboard` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def leaderboard(self, ctx: discord.ApplicationContext):
        """
        Basic method for sending the leaderboard to the channel that it was requested in.
        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_LEADERBOARD)

        leaderboard_view = LeaderBoardView(self.embed_manager)
        msg = self.embed_manager.get_leaderboard_embed(ctx.guild, 5)
        await ctx.respond(content=msg, view=leaderboard_view)


class BSEddiesHighScore(BSEddies):
    """
    Class for handling `/bseddies highscore` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def highscore(self, ctx: discord.ApplicationContext):
        """
        Basic method for sending the high score board to the channel that it was requested in.
        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_HIGHSCORES)

        highscore_view = HighScoreBoardView(self.embed_manager)
        msg = self.embed_manager.get_highscore_embed(ctx.guild, 5)
        await ctx.respond(content=msg, view=highscore_view)


class BSEddiesActive(BSEddies):
    """
    Class for handling `/active` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def active(self, ctx: discord.ApplicationContext) -> None:
        """
        Simple method for listing all the active bets in the system.

        This will actually show all bets that haven't been closed yet - not purely the active ones.

        We also make an effort to hide "private" bets that were created in private channels if the channel this
        command is being sent in isn't said private channel.

        :param ctx: the command context
        :return: None
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_ACTIVE)

        bets = self.user_bets.get_all_pending_bets(ctx.guild.id)

        message = "Here are all the active bets:\n"

        for bet in bets:
            if 'channel_id' not in bet or 'message_id' not in bet:
                continue

            if bet.get("private"):
                if bet["channel_id"] != ctx.channel_id:
                    continue

            link = f"https://discordapp.com/channels/{ctx.guild.id}/{bet['channel_id']}/{bet['message_id']}"

            add_text = "OPEN FOR NEW BETS" if bet.get("active") else "CLOSED - AWAITING RESULT"

            pt = f"**{bets.index(bet) + 1})** [{bet['bet_id']} - `{add_text}`] _{bet['title']}_\n{link}\n\n"
            message += pt

            if (len(message) + 400) > 2000 and bet != bets[-1]:
                await ctx.send(content=message)
                message = ""

        if len(bets) == 0:
            message = "There are no active bets :("

        await ctx.respond(content=message)


class BSEddiesPending(BSEddies):
    """
    Class for handling `/bseddies pending` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def pending(self, ctx: discord.ApplicationContext) -> None:
        """
        Simple method for listing all the pending bets for the user that executed this command

        A 'pending' bet is a bet that hasn't been closed or resolved the the user has invested eddies in to

        This will send an ephemeral message to the user with all their pending bets.

        :param ctx: slash command context
        :return: None
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_PENDING)

        bets = self.user_bets.get_all_pending_bets_for_user(ctx.author.id, ctx.guild.id)

        message = "Here are all your pending bets:\n"

        for bet in bets:
            if 'channel_id' not in bet or 'message_id' not in bet:
                continue

            link = f"https://discordapp.com/channels/{ctx.guild.id}/{bet['channel_id']}/{bet['message_id']}"

            add_text = "OPEN FOR NEW BETS" if bet.get("active") else "CLOSED - AWAITING RESULT"

            pt = (f"**{bets.index(bet) + 1})** [{bet['bet_id']} - `{add_text}`] _{bet['title']}_"
                  f"\nOutcome: {bet['betters'][str(ctx.author.id)]['emoji']}\n"
                  f"Points: **{bet['betters'][str(ctx.author.id)]['points']}**\n{link}\n\n")
            message += pt

            if (len(message) + 400) > 2000 and bet != bets[-1]:
                await ctx.respond(content=message, ephemeral=True)
                message = ""

        if len(bets) == 0:
            message = "You have no pending bets :("

        await ctx.respond(content=message, ephemeral=True)


class BSEddiesGift(BSEddies):
    """
    Class for handling `/bseddies gift` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def gift_eddies(self, ctx: discord.ApplicationContext,
                          friend: discord.User,
                          amount: int) -> None:
        """
        Function for handling a 'gift eddies' event.

        We make sure that the user initiating the command has enough BSEddies to give to a friend
        and then we simply increment their friend's BSEddies and decrement theirs.

        :param ctx: slash command context
        :param friend: discord.User for the friend to give eddies to
        :param amount: the amount of eddies to give
        :return: None
        """
        if not await self._handle_validation(ctx, friend=friend, amount=amount):
            return

        self._add_event_type_to_activity_history(
            ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_GIFT,
            friend_id=friend.id, amount=amount
        )

        points = self.user_points.get_user_points(ctx.author.id, ctx.guild.id)
        if points < amount:
            msg = f"You have insufficient points to perform that action."
            await ctx.respond(content=msg, ephemeral=True)
            return

        if not friend.dm_channel:
            await friend.create_dm()
        try:
            msg = f"**{ctx.author.name}** just gifted you `{amount}` eddies!!"
            await friend.send(content=msg)
        except discord.errors.Forbidden:
            pass

        self.user_points.decrement_points(ctx.author.id, ctx.guild.id, amount)
        self.user_points.increment_points(friend.id, ctx.guild.id, amount)

        # add to transaction history
        self.user_points.append_to_transaction_history(
            ctx.author.id,
            ctx.guild.id,
            {
                "type": TransactionTypes.GIFT_GIVE,
                "amount": amount * -1,
                "timestamp": datetime.datetime.now(),
                "user_id": friend.id,
            }
        )

        self.user_points.append_to_transaction_history(
            friend.id,
            ctx.guild.id,
            {
                "type": TransactionTypes.GIFT_RECEIVE,
                "amount": amount,
                "timestamp": datetime.datetime.now(),
                "user_id": ctx.author.id,
            }
        )

        await ctx.respond(content=f"Eddies transferred to `{friend.name}`!", ephemeral=True)


class BSEddiesCloseBet(BSEddies):
    """
    Class for handling `/bseddies bet close` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)
        self.bet_manager = BetManager(logger)

    async def create_bet_view(
            self,
            ctx: discord.ApplicationContext,
            bet_ids: list = None
    ):

        if not bet_ids:
            bet_ids = self.user_bets.query(
                {"closed": None, "guild_id": ctx.guild_id, "user": ctx.user.id},
                projection={"bet_id": True, "title": True, "created": True, "option_dict": True}
            )

        if len(bet_ids) == 0:
            try:
                await ctx.respond(content="You have no bets to close.", ephemeral=True)
            except AttributeError:
                await ctx.response.send_message(content="You have no bets to close.", ephemeral=True)
            return

        if len(bet_ids) > 25:
            bet_ids = sorted(bet_ids, key=lambda x: x["created"], reverse=True)
            bet_ids = bet_ids[:24]

        close_bet_view = CloseABetView(bet_ids, submit_callback=self.close_bet)
        try:
            await ctx.respond(content="**Closing a bet**", view=close_bet_view, ephemeral=True)
        except AttributeError:
            await ctx.response.send_message(content="**Closing a bet**", view=close_bet_view, ephemeral=True)

    async def close_bet(
            self,
            ctx: discord.Interaction,
            bet_id: str,
            emoji: str,) -> None:
        """
        This is the method for handling when we close a bet.

        We validate that the user initiating the command is the user who created the bet and that
        the bet is still open in the first place. We also make sure that the result the user
        provided us is actually a valid result for the bet.

        If that's all okay - we close the bet and dish out the BSEddies to the winners.
        We also inform the winners/losers what the result was and how many BSEddies they won (if any).

        :param ctx: slash command context
        :param bet_id: str - the BET ID
        :param emoji: str - the winning outcome emoji
        :return: None
        """

        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(
            ctx.user, ctx.guild_id, ActivityTypes.BSEDDIES_BET_CLOSE,
            bet_id=bet_id, emoji=emoji
        )

        guild = ctx.guild  # type: discord.Guild
        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)
        author = ctx.user

        if not bet:
            msg = f"This bet doesn't exist."
            await ctx.response.edit_message(content=msg, view=None)
            return

        if not bet["active"] and bet["result"] is not None:
            msg = f"You cannot close a bet that is already closed."
            await ctx.response.edit_message(content=msg, view=None)
            return

        if bet["user"] != author.id:
            msg = f"You cannot close a bet that isn't yours."
            await ctx.response.edit_message(content=msg, view=None)
            return

        emoji = emoji.strip()

        if emoji not in bet["option_dict"]:
            msg = f"{emoji} isn't a valid outcome so the bet can't be closed."
            await ctx.response.edit_message(content=msg, view=None)
            return

        # the logic in this if statement only applies if the user "won" their own bet and they were the only better
        # they just get refunded the eddies that put in
        if bet_dict := bet["betters"].get(str(author.id), None):
            if len(bet["betters"]) == 1 and bet_dict["emoji"] == emoji:

                self.logger.info(f"{ctx.user.id} just won a bet ({bet_id}) where they were the only better...")
                self.user_bets.close_a_bet(bet["_id"], emoji)
                self.user_points.increment_points(author.id, guild.id, bet_dict["points"])
                self.user_points.append_to_transaction_history(
                    ctx.user.id,
                    guild.id,
                    {
                        "type": TransactionTypes.BET_REFUND,
                        "amount": bet_dict["points"],
                        "timestamp": datetime.datetime.now(),
                        "bet_id": bet_id,
                        "comment": "User won their own bet when no-one else entered."
                    }
                )
                if not author.dm_channel:
                    await author.create_dm()
                try:
                    msg = (f"Looks like you were the only person to bet on your bet and you _happened_ to win it. "
                           f"As such, you have won **nothing**. However, you have been refunded the eddies that you "
                           f"originally bet.")
                    await author.send(content=msg)
                except discord.errors.Forbidden:
                    pass

                desc = (f"**{bet['title']}**\n\nThere were no winners on this bet. {author.mention} just _happened_ "
                        f"to win a bet they created and they were the only entry. They were refunded the amount of "
                        f"eddies that they originally bet.")
                # update the message to reflect that it's closed
                channel = guild.get_channel(bet["channel_id"])
                message = channel.get_partial_message(bet["message_id"])
                await message.edit(content=desc, view=None, embeds=[])
                await ctx.response.edit_message(content="Closed the bet for you!", view=None)
                return

        ret_dict = self.bet_manager.close_a_bet(bet_id, guild.id, emoji)

        desc = f"**{bet['title']}**\n{emoji} - **{ret_dict['outcome_name']['val']}** won!\n\n"

        for better in ret_dict["winners"]:
            desc += f"\n- {guild.get_member(int(better)).name} won `{ret_dict['winners'][better]}` eddies!"

        author = guild.get_member(ctx.user.id)

        # message the losers to tell them the bad news
        for loser in ret_dict["losers"]:
            mem = guild.get_member(int(loser))
            if not mem.dm_channel:
                await mem.create_dm()
            try:
                points_bet = ret_dict["losers"][loser]
                msg = (f"**{author.name}** just closed bet "
                       f"`[{bet_id}] - {bet['title']}` and the result was {emoji} "
                       f"(`{ret_dict['outcome_name']['val']})`.\n"
                       f"As this wasn't what you voted for - you have lost. You bet **{points_bet}** eddies.")
                await mem.send(content=msg)
            except discord.errors.Forbidden:
                pass

        # message the winners to tell them the good news
        for winner in ret_dict["winners"]:
            mem = guild.get_member(int(winner))
            if not mem.dm_channel:
                await mem.create_dm()
            try:
                msg = (f"**{author.name}** just closed bet "
                       f"`[{bet_id}] - {bet['title']}` and the result was {emoji} "
                       f"(`{ret_dict['outcome_name']['val']})`.\n"
                       f"**This means you won!!** "
                       f"You have won `{ret_dict['winners'][winner]}` BSEDDIES!!")
                await mem.send(content=msg)
            except discord.errors.Forbidden:
                pass

        # update the message to reflect that it's closed
        channel = guild.get_channel(bet["channel_id"])
        message = channel.get_partial_message(bet["message_id"])
        await message.edit(content=desc, view=None, embeds=[])
        await ctx.response.edit_message(content="Closed the bet for you!", view=None)


class BSEddiesCreateBet(BSEddies):
    """
    Class for handling `/bseddies bet create` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)
        self.multiple_options_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣"]

    async def handle_bet_creation(
            self,
            ctx: Union[discord.ApplicationContext, discord.Interaction],
            bet_title: str,
            option_one_name: Union[str, None] = None,
            option_two_name: Union[str, None] = None,
            option_three_name: Union[str, None] = None,
            option_four_name: Union[str, None] = None,
            option_five_name: Union[str, None] = None,
            option_six_name: Union[str, None] = None,
            option_seven_name: Union[str, None] = None,
            option_eight_name: Union[str, None] = None,
            option_nine_name: Union[str, None] = None,
            option_ten_name: Union[str, None] = None,
            timeout_str: Union[str, None] = None,
            autogenerated: bool = False,
            bseddies_place=None,
            bseddies_close=None
    ) -> None:
        """
        The method that handles bet creation.

        We work out which outcome names we're gonna need - either custom or defaults.
        We make sure the user provided the right timeout or outcomes names (if at all).
        We then set the timeout for the bet.
        And we also work out which outcome emojis to use based of of the number of provided outcomes.

        Then we create the bet and send a message to channel the bet was created in.

        :param bseddies_place:
        :param bseddies_close:
        :param ctx:
        :param bet_title:
        :param option_one_name:
        :param option_two_name:
        :param option_three_name:
        :param option_four_name:
        :param option_six_name:
        :param option_five_name:
        :param option_seven_name:
        :param option_eight_name:
        :param option_nine_name:
        :param option_ten_name:
        :param timeout_str:
        :param autogenerated:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        await ctx.response.defer(ephemeral=True)

        self._add_event_type_to_activity_history(
            ctx.user, ctx.guild_id, ActivityTypes.BSEDDIES_BET_CREATE,
            bet_title=bet_title, option_one_name=option_one_name, option_two_name=option_two_name,
            option_three_name=option_three_name, option_four_name=option_four_name, option_five_name=option_five_name,
            option_six_name=option_six_name, autogenerated=autogenerated, timeout_str=timeout_str
        )

        if not option_one_name or not option_two_name:
            msg = (f"If you're providing custom outcome names - you must provide at least two outcomes.\n"
                   f"Additionally, you must provide the outcomes sequentially "
                   f"(ie, outcome_one, then outcome_two, and then outcome_three, and then outcome_four.)")
            await ctx.respond(content=msg, ephemeral=True)
            return

        option_dict = {
            self.multiple_options_emojis[0]: {"val": option_one_name},
            self.multiple_options_emojis[1]: {"val": option_two_name},
        }

        if option_three_name:
            option_dict[self.multiple_options_emojis[2]] = {"val": option_three_name}
        if option_four_name:
            option_dict[self.multiple_options_emojis[3]] = {"val": option_four_name}
        if option_five_name:
            option_dict[self.multiple_options_emojis[4]] = {"val": option_five_name}
        if option_six_name:
            option_dict[self.multiple_options_emojis[5]] = {"val": option_six_name}
        if option_seven_name:
            option_dict[self.multiple_options_emojis[6]] = {"val": option_seven_name}
        if option_eight_name:
            option_dict[self.multiple_options_emojis[7]] = {"val": option_eight_name}
        if option_nine_name:
            option_dict[self.multiple_options_emojis[8]] = {"val": option_nine_name}
        if option_ten_name:
            option_dict[self.multiple_options_emojis[8]] = {"val": option_ten_name}

        if timeout_str is None:
            timeout = datetime.datetime.now() + datetime.timedelta(minutes=10)
        else:
            timeout_str = timeout_str.strip()
            match = re.match(r"\d{1,5}([smhd])", timeout_str)
            if not match:
                msg = ("Your timeout string was incorrectly formatted. Needs to be 1 - 5 digits "
                       "and then either a s, m, h, or d "
                       "to signify seconds, minutes, hours, or days respectively.")
                await ctx.respond(content=msg, ephemeral=True)
                return
            g = match.group()
            if "s" in g:
                dt_key = {"seconds": int(g.replace("s", ""))}
            elif "m" in g:
                dt_key = {"minutes": int(g.replace("m", ""))}
            elif "h" in g:
                dt_key = {"hours": int(g.replace("h", ""))}
            elif "d" in g:
                dt_key = {"days": int(g.replace("d", ""))}
            else:
                dt_key = {}
            timeout = datetime.datetime.now() + datetime.timedelta(**dt_key)

        private = ctx.channel_id in PRIVATE_CHANNEL_IDS

        bet = self.user_bets.create_new_bet(
            ctx.guild.id,
            ctx.user.id,
            bet_title,
            options=list(option_dict.keys()),
            option_dict=option_dict,
            timeout=timeout,
            private=private
        )

        embed = self.embed_manager.get_bet_embed(ctx.guild, bet["bet_id"], bet)

        member = ctx.guild.get_member(ctx.user.id)
        content = f"Bet created by {member.mention}"

        bet_view = BetView(bet, bseddies_place, bseddies_close)

        # await ctx.send(content=f"Bet created: {bet_title}", hidden=True)
        message = await ctx.channel.send(content=content, embed=embed, view=bet_view)

        self.user_bets.update(
            {"_id": bet["_id"]},
            {"$set": {"message_id": message.id, "channel_id": message.channel.id}}
        )

        await ctx.followup.send(content="Created bet for you.", ephemeral=True)


class BSEddiesPlaceBet(BSEddies):
    """
    Class for handling `/bseddies bet place` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def create_bet_view(
            self,
            ctx: Union[discord.ApplicationContext, discord.Interaction],
            bet_ids: list = None
    ):

        if not bet_ids:
            bet_ids = self.user_bets.query(
                {"active": True, "guild_id": ctx.guild_id},
                projection={"bet_id": True, "title": True, "option_dict": True}
            )

        if len(bet_ids) == 0:
            try:
                await ctx.respond(content="There are no active bets to bet on right now.", ephemeral=True)
            except AttributeError:
                await ctx.response.send_message(content="There are no active bets to bet on right now.", ephemeral=True)
            return

        points = self.user_points.get_user_points(
            ctx.user.id, ctx.guild_id
        )

        place_bet_view = PlaceABetView(bet_ids, points, submit_callback=self.place_bet)
        try:
            await ctx.respond(content="**Placing a bet**", view=place_bet_view, ephemeral=True)
        except AttributeError:
            await ctx.response.send_message(content="**Placing a bet**", view=place_bet_view, ephemeral=True)

    async def place_bet(
            self,
            ctx: discord.Interaction,
            bet_id: str,
            amount: int,
            emoji: str,
    ) -> Union[None, bool]:
        """
        Main method for placing a bet.

        Validates that a bet exists, is active and that the user has the right amount of BSEddies.
        It also checks that the bet being placed is either new, or the same as the existing bet the user
        has for this bet.

        :param ctx:
        :param bet_id:
        :param amount:
        :param emoji:
        :return: None or a bool
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(
            ctx.user, ctx.guild_id, ActivityTypes.BSEDDIES_BET_PLACE,
            bet_id=bet_id, amount=amount, emoji=emoji
        )

        response = ctx.response  # type: discord.InteractionResponse

        guild = ctx.guild  # type: discord.Guild
        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)

        if not bet:
            msg = f"This bet doesn't exist."
            await response.edit_message(content=msg, view=None)
            return

        if not bet["active"]:
            msg = f"Your reaction on **Bet {bet_id}** failed as the bet is closed for new bets."
            await response.edit_message(content=msg, view=None)
            return

        emoji = emoji.strip()

        if emoji not in bet["option_dict"]:
            msg = f"Your reaction on **Bet {bet_id}** failed as that reaction isn't a valid outcome."
            await response.edit_message(content=msg, view=None)
            return

        if amount <= 0:
            msg = f"Cannot bet negative eddies or 0 eddies."
            await response.edit_message(content=msg, view=None)
            return

        success = self.user_bets.add_better_to_bet(bet_id, guild.id, ctx.user.id, emoji, amount)

        if not success["success"]:
            msg = f"Your bet on **Bet {bet_id}** failed cos __{success['reason']}__?"
            await response.edit_message(content=msg, view=None)
            return False

        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)
        channel = guild.get_channel(bet["channel_id"])
        message = channel.get_partial_message(bet["message_id"])
        embed = self.embed_manager.get_bet_embed(guild, bet_id, bet)
        self.user_points.append_to_transaction_history(
            ctx.user.id,
            guild.id,
            {
                "type": TransactionTypes.BET_PLACE,
                "amount": amount * -1,
                "timestamp": datetime.datetime.now(),
                "bet_id": bet_id,
                "comment": "Bet placed through slash command",
            }
        )
        await message.edit(embed=embed)
        await response.edit_message(content="Placed the bet for you!", view=None)


class BSEddiesTransactionHistory(BSEddies):
    """
    Class for handling `/bseddies transactions` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    @staticmethod
    async def _handle_recent_trans(ctx: discord.ApplicationContext, transaction_history: list) -> None:
        """
        This handles our 'recent transaction history' command. We take the last ten items in the transaction history and
        build a nice formatted ephemeral message with it and send it to the user.
        :param ctx:
        :param transaction_history:
        :return:
        """
        recent_history = transaction_history[-10:]

        message = "This is your recent transaction history.\n"

        for item in recent_history:
            message += (
                f"\n"
                f"**Timestamp**: {item['timestamp'].strftime('%d %b %y %H:%M:%S')}\n"
                f"**Transaction Type**: {TransactionTypes(item['type']).name}\n"
                f"**Change amount**: {item['amount']}\n"
                f"**Running eddies total**: {item['points']}\n"
                f"**Comment**: {item.get('comment', 'No comment')}\n"
            )

            if b_id := item.get("bet_id"):
                message += f"**Bet ID**: {b_id}\n"

            if l_id := item.get("loan_id"):
                message += f"**Loan ID**: {l_id}\n"

            if u_id := item.get("user_id"):
                message += f"**User ID**: {u_id}\n"

        await ctx.respond(content=message, ephemeral=True)

    @staticmethod
    async def _handle_full_trans(ctx: discord.ApplicationContext, transaction_history: list) -> None:
        """
        Method for handling out "full transaction history" command

        This mostly just builds an XLSX file that we can send to the user. We use the XLSXWRITER library to do the
        heavy lifting here.

        Once we've created the file, we send it to the user in a DM and send an ephemeral message to let the user know.
        Ephemeral messages don't support file attachments yet.
        :param ctx:
        :param transaction_history:
        :return:
        """
        path = os.path.join(os.path.expanduser("~"), "trans_files")
        f_name = f"full_trans_{ctx.author.id}.xlsx"

        if not os.path.exists(path):
            os.makedirs(path)

        full_name = os.path.join(path, f_name)

        workbook = xlsxwriter.Workbook(full_name)
        worksheet = workbook.add_worksheet("Transaction History")

        cols = ["Item", "Type", "Timestamp", "Change amount", "Eddies", "Bet ID", "Loan ID", "User ID", "Comment"]
        worksheet.write_row(0, 0, cols, workbook.add_format({"bold": True}))

        row = 1
        for item in transaction_history:
            worksheet.write_row(
                row, 0,
                [row, TransactionTypes(item['type']).name, item['timestamp'].strftime('%d %b %y %H:%M:%S'),
                 item["amount"], item["points"], item.get("bet_id", "N/A"), item.get("loan_id", "N/A"),
                 item.get("user_id", "N/A"), item.get("comment", "No comment")]
            )
            row += 1

        center_format = workbook.add_format()
        center_format.set_align('center')
        center_format.set_align('vcenter')

        worksheet.set_column("A:A", cell_format=center_format)
        worksheet.set_column("B:B", width=18)
        worksheet.set_column("C:D", width=20)
        worksheet.set_column("I:I", width=50)

        workbook.close()

        try:
            await ctx.author.send(content="Here's your full transaction history:", file=discord.File(full_name, f_name))
        except discord.Forbidden:
            # user doesn't allow DMs
            pass

        await ctx.respond(content="I've sent you a DM with your full history.", ephemeral=True)

    async def transaction_history(self, ctx: discord.ApplicationContext, full: Union[str, None]) -> None:
        """
        Gets the user history and takes the last 10 entries and then displays that list to the user
        :param ctx:
        :param full:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(
            ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_TRANSACTIONS, full=full
        )

        user = self.user_points.find_user(ctx.author.id, ctx.guild.id)
        transaction_history = user["transaction_history"]

        amount = 0
        for item in transaction_history:
            if transaction_history.index(item) == 0:
                item["points"] = item["amount"]
                amount = item["amount"]
                continue
            amount += item["amount"]
            item["points"] = amount

        if full is None:
            await self._handle_recent_trans(ctx, transaction_history)
        else:
            await self._handle_full_trans(ctx, transaction_history)


class BSEddiesPredict(BSEddies):
    """
    Class for handling `/bseddies predict` command
    """

    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)
        self.manager = BSEddiesManager(client, logger)

    async def predict(self, ctx: discord.ApplicationContext) -> None:
        """
        Command to allow a user to see how many eddies they might gain today.
        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        await ctx.defer(ephemeral=True)

        self._add_event_type_to_activity_history(
            ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_PREDICT
        )

        start, end = self.manager.get_datetime_objects()

        start = start + datetime.timedelta(days=1)
        end = end + datetime.timedelta(days=1)

        eddies_dict = self.manager.give_out_eddies(ctx.guild_id, False)

        eddies = eddies_dict[ctx.author.id][0]
        breakdown = eddies_dict[ctx.author.id][1]
        tax = eddies_dict[ctx.author.id][2]

        king_id = self.user_points.get_current_king(ctx.guild_id)["uid"]

        if king_id == ctx.author.id:
            tax_message = f"You're estimated to gain `{tax}` from tax gains."
        else:
            tax_message = f"You're estimated to be taxed `{tax}` by the KING"

        message = (
            f"You're estimated to gain `{eddies}` (after tax) today.\n"
            f"{tax_message}\n"
            f"\n"
            f"This is based on the following amount of interactivity today:"
        )

        for key in sorted(breakdown):
            message += f"\n - `{HUMAN_MESSAGE_TYPES[key]}`  :  **{breakdown[key]}**"

        await ctx.followup.send(content=message, ephemeral=True)


class BSEddiesAdminGive(BSEddies):
    """
    Class for handling `/bseddies admin give` command
    """

    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def admin_give(self, ctx: discord.ApplicationContext, user: discord.User, amount: int) -> None:
        """
        Command to give a user some extra eddies.
        :param ctx:
        :param user:
        :param amount:
        :return:
        """
        if not await self._handle_validation(ctx, admin=True):
            return

        self._add_event_type_to_activity_history(
            ctx.user, ctx.guild_id, ActivityTypes.BSEDDIES_ADMIN_GIVE, user_id=user.id, amount=amount
        )

        self.user_points.increment_points(user.id, ctx.guild.id, amount)

        self.user_points.append_to_transaction_history(
            user.id, ctx.guild.id,
            {
                "type": TransactionTypes.ADMIN_GIVE,
                "amount": amount,
                "timestamp": datetime.datetime.now(),
                "comment": "Admin override increment"
            }
        )

        try:
            await user.send(content=f"You've been given {amount} eddies by an admin.")
        except discord.Forbidden:
            pass

        await ctx.respond(content=f"Given {user.display_name} {amount} eddies.", ephemeral=True)


class BSEddiesKing(BSEddies):
    """
        Class for handling `/bseddies admin give` command
        """

    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def king_data(self, ctx: discord.ApplicationContext) -> None:
        """

        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        self._add_event_type_to_activity_history(ctx.author, ctx.guild_id, ActivityTypes.BSEDDIES_KING)

        guild_id = ctx.guild.id

        king_user = self.user_points.get_current_king(guild_id)
        data = self.user_points.get_king_info(king_user)

        role_id = BSEDDIES_KING_ROLES[guild_id]
        role = ctx.guild.get_role(role_id)
        member = ctx.guild.get_member(king_user["uid"])  # type: discord.Member

        message = (f"**King Info**\n"
                   f"{member.mention} is our current {role.mention}. They've been King for "
                   f"{str(datetime.timedelta(seconds=data['current']))}.\n\n"
                   f"The total amount of time they've spent as KING is "
                   f"`{str(datetime.timedelta(seconds=data['total']))}`\n"
                   f"They've been {role.mention} **{data['times']}** times.\n"
                   f"The longest they've been {role.mention} for is "
                   f"{str(datetime.timedelta(seconds=max(data['all_times'])))}")
        await ctx.respond(content=message)

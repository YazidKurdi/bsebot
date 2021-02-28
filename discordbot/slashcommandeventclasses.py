"""
File for Slash Command Event Classes

Each class in this file corresponds to a slash command that we've register in commandmanager.CommandManager
These classes handle most of the logic for them
"""

import copy
import datetime
import math
import os
import re
from typing import Union

import discord
import discord_slash
import xlsxwriter

from discordbot.betmanager import BetManager
from discordbot.bot_enums import TransactionTypes, ActivityTypes
from discordbot.clienteventclasses import BaseEvent
from discordbot.constants import BETA_USERS, CREATOR, PRIVATE_CHANNEL_IDS


class BSEddies(BaseEvent):
    """
    A base BSEddies event for any shared methods across
    All slash command classes will inherit from this class
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def _handle_validation(self, ctx: discord_slash.context.SlashContext, **kwargs) -> bool:
        """
        Internal method for validating slash command inputs.
        :param ctx: discord ctx to use
        :param kwargs: the additional kwargs to use in validation
        :return: True or False
        """
        if ctx.guild.id not in self.guild_ids:
            return False

        if "friend" in kwargs and (
                isinstance(kwargs["friend"], discord.User) or isinstance(kwargs["friend"], discord.Member)):
            if kwargs["friend"].bot:
                msg = f"Bots cannot be gifted eddies."
                await ctx.send(content=msg, hidden=True)
                return False

            if kwargs["friend"].id == ctx.author.id:
                msg = f"You can't gift yourself points."
                await ctx.send(content=msg, hidden=True)
                return False

        if "amount" in kwargs and isinstance(kwargs["amount"], int):
            if kwargs["amount"] < 0:
                msg = f"You can't _\"gift\"_ someone negative points."
                await ctx.send(content=msg, hidden=True)
                return False

        return True


class BSEddiesView(BSEddies):
    """
    Class for handling `/bseddies view` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def view(self, ctx):
        """
        Basic view method for handling view slash commands.

        Sends an ephemeral message to the user with their total eddies and any "pending" eddies they
        have tied up in bets.

        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        points = self.user_points.get_user_points(ctx.author.id, ctx.guild.id)
        pending = self.user_bets.get_user_pending_points(ctx.author.id, ctx.guild.id)
        msg = (f"You have **{points}** :money_with_wings:`BSEDDIES`:money_with_wings:!"
               f"\nAdditionally, you have `{pending}` points on 'pending bets'.")
        await ctx.send(content=msg, hidden=True)


class BSEddiesLeaderboard(BSEddies):
    """
    Class for handling `/bseddies leaderboard` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def leaderboard(self, ctx):
        """
        Basic method for sending the leaderboard to the channel that it was requested in.
        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        embed = self.embed_manager.get_leaderboard_embed(ctx.guild, 5)
        message = await ctx.channel.send(content=embed)
        await message.add_reaction(u"▶️")


class BSEddiesActive(BSEddies):
    """
    Class for handling `/bseddies active` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def active(self, ctx: discord_slash.context.SlashContext) -> None:
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

        if len(bets) == 0:
            message = "There are no active bets :("

        await ctx.send(content=message)


class BSEddiesPending(BSEddies):
    """
    Class for handling `/bseddies pending` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def pending(self, ctx: discord_slash.context.SlashContext) -> None:
        """
        Simple method for listing all the pending bets for the user that executed this command

        A 'pending' bet is a bet that hasn't been closed or resolved the the user has invested eddies in to

        This will send an ephemeral message to the user with all their pending bets.

        :param ctx: slash command context
        :return: None
        """
        if not await self._handle_validation(ctx):
            return

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

        if len(bets) == 0:
            message = "You have no pending bets :("

        await ctx.send(content=message, hidden=True)


class BSEddiesGift(BSEddies):
    """
    Class for handling `/bseddies gift` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def gift_eddies(self, ctx: discord_slash.context.SlashContext,
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

        points = self.user_points.get_user_points(ctx.author.id, ctx.guild.id)
        if points < amount:
            msg = f"You have insufficient points to perform that action."
            await ctx.send(content=msg, hidden=True)
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

        await ctx.send(content=f"Eddies transferred to `{friend.name}`!", hidden=True)


class BSEddiesCloseBet(BSEddies):
    """
    Class for handling `/bseddies bet close` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)
        self.bet_manager = BetManager(logger)

    async def close_bet(
            self,
            ctx: discord_slash.context.SlashContext,
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

        guild = ctx.guild  # type: discord.Guild
        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)
        author = ctx.author

        if not bet:
            msg = f"This bet doesn't exist."
            await ctx.send(content=msg, hidden=True)
            return

        if not bet["active"] and bet["result"] is not None:
            msg = f"You cannot close a bet that is already closed."
            await ctx.send(content=msg, hidden=True)
            return

        if bet["user"] != author.id:
            msg = f"You cannot close a bet that isn't yours."
            await ctx.send(content=msg, hidden=True)
            return

        emoji = emoji.strip()

        if emoji not in bet["option_dict"]:
            msg = f"{emoji} isn't a valid outcome so the bet can't be closed."
            await ctx.send(content=msg, hidden=True)
            return

        # the logic in this if statement only applies if the user "won" their own bet and they were the only better
        # they just get refunded the eddies that put in
        if bet_dict := bet["betters"].get(str(author.id), None):
            if len(bet["betters"]) == 1 and bet_dict["emoji"] == emoji:

                self.logger.info(f"{ctx.author.id} just won a bet ({bet_id}) where they were the only better...")
                self.user_bets.close_a_bet(bet["_id"], emoji)
                self.user_points.increment_points(author.id, guild.id, bet_dict["points"])
                self.user_points.append_to_transaction_history(
                    ctx.author.id,
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
                await message.edit(content=desc, embed=None)
                return

        ret_dict = self.bet_manager.close_a_bet(bet_id, guild.id, emoji)

        desc = f"**{bet['title']}**\n{emoji} - **{ret_dict['outcome_name']['val']}** won!\n\n"

        for better in ret_dict["winners"]:
            desc += f"\n- {guild.get_member(int(better)).name} won `{ret_dict['winners'][better]}` eddies!"

        author = guild.get_member(ctx.author.id)

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
        await message.edit(content=desc, embed=None)


class BSEddiesCreateBet(BSEddies):
    """
    Class for handling `/bseddies bet create` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)
        self.default_two_options = {"1️⃣": {"val": "succeed"}, "2️⃣": {"val": "fail"}}
        self.multiple_options_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]

    async def handle_bet_creation(
            self,
            ctx: discord_slash.context.SlashContext,
            bet_title: str,
            option_one_name: Union[str, None] = None,
            option_two_name: Union[str, None] = None,
            option_three_name: Union[str, None] = None,
            option_four_name: Union[str, None] = None,
            option_five_name: Union[str, None] = None,
            option_six_name: Union[str, None] = None,
            timeout_str: Union[str, None] = None,
    ) -> None:
        """
        The method that handles bet creation.

        We work out which outcome names we're gonna need - either custom or defaults.
        We make sure the user provided the right timeout or outcomes names (if at all).
        We then set the timeout for the bet.
        And we also work out which outcome emojis to use based of of the number of provided outcomes.

        Then we create the bet and send a message to channel the bet was created in.

        :param ctx:
        :param bet_title:
        :param option_one_name:
        :param option_two_name:
        :param option_three_name:
        :param option_four_name:
        :param option_six_name:
        :param option_five_name:
        :param timeout_str:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        user = self.user_points.find_user(ctx.author.id, ctx.guild.id, projection={"king": True, "points": True})
        points = user["points"]
        max_bets = (math.floor(points / 100.0) * 100) / 50
        current_bets = self.user_bets.query(
            {"guild_id": ctx.guild.id,
             "user": ctx.author.id,
             "result": None
             },
            projection={"_id": True}
        )

        current_bets = len(current_bets)

        if max_bets == 0:
            max_bets = 2

        if ctx.author.id in BETA_USERS:
            max_bets += 2

        if ctx.author.id == CREATOR:
            max_bets += 2

        if user.get("king", False):
            max_bets += 2

        if current_bets and current_bets > max_bets:
            msg = (f"The maximum number of open bets allowed is determined by your BSEddie total. The more you have,"
                   f" the more open bets you're allowed to maintain. It looks like you already have the maximum "
                   f"number of open bets. You'll have to wait until they're closed or you have more BSEddies.")
            await ctx.send(content=msg, hidden=True)
            return

        if (option_one_name and not option_two_name) or (not option_one_name and option_two_name):
            msg = (f"If you're providing custom outcome names - you must provide at least two outcomes.\n"
                   f"Additionally, you must provide the outcomes sequentially "
                   f"(ie, outcome_one, then outcome_two, and then outcome_three, and then outcome_four.)")
            await ctx.send(content=msg, hidden=True)
            return

        if not option_one_name and not option_two_name:
            option_dict = copy.deepcopy(self.default_two_options)
        elif (option_one_name and option_two_name) and not option_three_name:
            option_dict = copy.deepcopy(self.default_two_options)
            keys = list(option_dict.keys())
            option_dict[keys[0]]["val"] = option_one_name
            option_dict[keys[1]]["val"] = option_two_name
        elif option_one_name and option_two_name and option_three_name:
            option_dict = {self.multiple_options_emojis[0]: {"val": option_one_name},
                           self.multiple_options_emojis[1]: {"val": option_two_name},
                           self.multiple_options_emojis[2]: {"val": option_three_name}}
            if option_four_name:
                option_dict[self.multiple_options_emojis[3]] = {"val": option_four_name}
            if option_five_name:
                option_dict[self.multiple_options_emojis[4]] = {"val": option_five_name}
            if option_six_name:
                option_dict[self.multiple_options_emojis[5]] = {"val": option_six_name}
        else:
            msg = (f"If you're providing custom outcome names - you must provide at least two outcomes.\n"
                   f"Additionally, you must provide the outcomes sequentially "
                   f"(ie, outcome_one, then outcome_two, and then outcome_three, and then outcome_four.)")
            await ctx.send(content=msg, hidden=True)
            return

        if timeout_str is None:
            timeout = datetime.datetime.now() + datetime.timedelta(minutes=10)
        else:
            timeout_str = timeout_str.strip()
            match = re.match(r"\d{1,5}(s|m|h|d)", timeout_str)
            if not match:
                msg = ("Your timeout string was incorrectly formatted. Needs to be 1 - 5 digits "
                       "and then either a s, m, h, or d "
                       "to signify seconds, minutes, hours, or days respectively.")
                await ctx.send(content=msg, hidden=True)
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
            ctx.author.id,
            bet_title,
            options=list(option_dict.keys()),
            option_dict=option_dict,
            timeout=timeout,
            private=private
        )

        embed = self.embed_manager.get_bet_embed(ctx.guild, bet["bet_id"], bet)

        member = ctx.guild.get_member(ctx.author.id)
        # embed.set_author(name=member.name)

        content = f"Bet created by {member.mention}"

        # await ctx.send(content=f"Bet created: {bet_title}", hidden=True)
        message = await ctx.channel.send(content=content, embed=embed)

        self.user_bets.update(
            {"_id": bet["_id"]},
            {"$set": {"message_id": message.id, "channel_id": message.channel.id}}
        )
        for emoji in option_dict:
            await message.add_reaction(emoji)


class BSEddiesPlaceEvent(BSEddies):
    """
    Class for handling `/bseddies bet place` commands
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def place_bet(
            self,
            ctx: discord_slash.context.SlashContext,
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

        guild = ctx.guild  # type: discord.Guild
        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)

        if not bet:
            msg = f"This bet doesn't exist."
            await ctx.send(content=msg, hidden=True)
            return

        if not bet["active"]:
            msg = f"Your reaction on **Bet {bet_id}** failed as the bet is closed for new bets."
            await ctx.send(content=msg, hidden=True)
            return

        emoji = emoji.strip()

        if emoji not in bet["option_dict"]:
            msg = f"Your reaction on **Bet {bet_id}** failed as that reaction isn't a valid outcome."
            await ctx.send(content=msg, hidden=True)
            return

        success = self.user_bets.add_better_to_bet(bet_id, guild.id, ctx.author.id, emoji, amount)

        if not success["success"]:
            msg = f"Your reaction on **Bet {bet_id}** failed cos __{success['reason']}__?"
            await ctx.send(content=msg, hidden=True)
            return False

        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)
        channel = guild.get_channel(bet["channel_id"])
        message = channel.get_partial_message(bet["message_id"])
        embed = self.embed_manager.get_bet_embed(guild, bet_id, bet)
        self.user_points.append_to_transaction_history(
            ctx.author.id,
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


class BSEddiesTransactionHistory(BSEddies):
    """
    Class for handling `/bseddies transactions` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    @staticmethod
    async def _handle_recent_trans(ctx: discord_slash.context.SlashContext, transaction_history: list) -> None:
        """
        This handles our 'recent transaction history' command. We take the last ten items in the transaction history and
        build a nice formatted ephemeral message with it and send it to the user.
        :param ctx:
        :param transaction_history:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        user = self.user_points.find_user(ctx.author.id, ctx.guild.id)
        transaction_history = user["transaction_history"]
        recent_history = transaction_history[-10:]

        message = "This is your recent transaction history.\n"

        starting_points = user["points"]
        for item in reversed(recent_history):
            starting_points + (item["amount"] * -1)

        for item in recent_history:
            if recent_history.index(item) != 1:
                starting_points += (item["amount"] * -1)

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

        await ctx.send(content=message, hidden=True)

    @staticmethod
    async def _handle_full_trans(ctx: discord_slash.context.SlashContext, transaction_history: list) -> None:
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

        await ctx.send(content="I've sent you a DM with your full history.", hidden=True)

    async def transaction_history(self, ctx: discord_slash.context.SlashContext, full: Union[str, None]) -> None:
        """
        Gets the user history and takes the last 10 entries and then displays that list to the user
        :param ctx:
        :param full:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

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


class BSEddiesNotifcationToggle(BSEddies):
    """
    Class for handling `/bseddies notifcations` command
    """
    def __init__(self, client, guilds, logger, beta_mode=False):
        super().__init__(client, guilds, logger, beta_mode=beta_mode)

    async def notification_toggle(self, ctx: discord_slash.context.SlashContext) -> None:
        """
        Function for allowing the user to toggle whether they get daily salary notifications.
        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        user_id = ctx.author.id
        guild_id = ctx.guild.id

        user = self.user_points.find_user(user_id, guild_id)

        notification_setting = user.get("daily_eddies", False)

        notification_setting = not notification_setting

        self.user_points.set_daily_eddies_toggle(user_id, guild_id, notification_setting)

        message = f"Your daily salary notifications have now been turned **{'ON' if notification_setting else 'OFF'}**."

        await ctx.send(content=message, hidden=True)

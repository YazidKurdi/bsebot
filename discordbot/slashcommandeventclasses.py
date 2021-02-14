import copy
import datetime
import re

import discord
import discord_slash

from discordbot.clienteventclasses import BaseEvent
from discordbot.embedmanager import EmbedManager
from mongo.bsepoints import UserBets, UserPoints


class BSEddies(BaseEvent):
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)

    async def _handle_validation(self, ctx: discord_slash.context.SlashContext, **kwargs):
        """
        Internal method for validating slash command inputs.
        :param ctx:
        :return:
        """
        if ctx.guild.id not in self.guild_ids:
            return False

        if self.beta_mode and ctx.channel.id != 809773876078575636:
            msg = f"These features are in BETA mode and this isn't a BETA channel."
            await ctx.send(content=msg, hidden=True)
            return False

        if "friend" in kwargs and isinstance(kwargs["friend"], discord.User):
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
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)

    async def view(self, ctx):
        """
        Basic view method for handling view slash commands.
        If validation passes - it will inform the user of their current Eddies total.
        :param ctx:
        :return:
        """
        if not await self._handle_validation(ctx):
            return

        points = self.user_points.get_user_points(ctx.author.id, ctx.guild.id)
        msg = f"You have **{points}** :money_with_wings:`BSEDDIES`:money_with_wings:!"
        await ctx.send(content=msg, hidden=True)


class BSEddiesLeaderboard(BSEddies):
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)

    async def leaderboard(self, ctx):
        if not await self._handle_validation(ctx):
            return

        embed = self.embed_manager.get_leaderboard_embed(ctx.guild, 5)
        message = await ctx.channel.send(content=embed)
        await message.add_reaction(u"▶️")


class BSEddiesActive(BSEddies):
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)

    async def active(self, ctx):
        if not await self._handle_validation(ctx):
            return

        bets = self.user_bets.get_all_active_bets(ctx.guild.id)

        message = "Here are all the active bets:\n"

        for bet in bets:
            if 'channel_id' not in bet or 'message_id' not in bet:
                continue

            link = f"https://discordapp.com/channels/{ctx.guild.id}/{bet['channel_id']}/{bet['message_id']}"

            pt = f"**{bets.index(bet) + 1})** [{bet['bet_id']}] _{bet['title']}_\n{link}\n\n"
            message += pt

        if len(bets) == 0:
            message = "There are no active bets :("

        await ctx.send(content=message)


class BSEddiesGift(BSEddies):
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)

    async def gift_eddies(self, ctx,
                          friend: discord.User,
                          amount: int):
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

        await ctx.send(content=f"Eddies transferred to `{friend.name}`!", hidden=True)


class BSEddiesCloseBet(BSEddies):
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)

    async def close_bet(
            self,
            ctx: discord_slash.context.SlashContext,
            bet_id: str,
            emoji: str,):

        if not await self._handle_validation(ctx):
            return

        guild = ctx.guild  # type: discord.Guild
        bet = self.user_bets.get_bet_from_id(guild.id, bet_id)

        if not bet["active"] and bet["result"] is not None:
            msg = f"You cannot close a bet that is already closed."
            await ctx.send(content=msg, hidden=True)
            return

        if bet["user"] != ctx.author.id:
            msg = f"You cannot close a bet that isn't yours."
            await ctx.send(content=msg, hidden=True)
            return

        emoji = emoji.strip()

        if emoji not in bet["option_dict"]:
            msg = f"{emoji} isn't a valid outcome so the bet can't be closed."
            await ctx.send(content=msg, hidden=True)
            return

        ret_dict = self.user_bets.close_a_bet(bet_id, guild.id, emoji)

        desc = f"**{bet['title']}**\n{emoji} won!\n\n"

        for better in ret_dict["winners"]:
            desc += f"\n- {guild.get_member(int(better)).name} won `{ret_dict['winners'][better]}` eddies!"

        author = guild.get_member(ctx.author.id)

        # message the losers to tell them the bad news
        for loser in ret_dict["losers"]:
            mem = guild.get_member(int(loser))
            if not mem.dm_channel:
                await mem.create_dm()
            try:
                msg = (f"**{author.name}** just closed bet "
                       f"`[{bet_id}] - {bet['title']}` and the result was {emoji}.\n"
                       f"As this wasn't what you voted for - you have lost.")
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
                       f"`[{bet_id}] - {bet['title']}` and the result was {emoji}.\n"
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
    def __init__(self, client, guilds, beta_mode=False):
        super().__init__(client, guilds, beta_mode=beta_mode)
        self.default_two_options = {"1️⃣": {"val": "succeed"}, "2️⃣": {"val": "fail"}}
        self.multiple_options_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

    async def handle_bet_creation(
            self,
            ctx: discord_slash.context.SlashContext,
            bet_title: str,
            option_one_name=None,
            option_two_name=None,
            option_three_name=None,
            option_four_name=None,
            timeout_str=None
    ):
        if not await self._handle_validation(ctx):
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
        else:
            msg = (f"If you're providing custom outcome names - you must provide at least two outcomes.\n"
                   f"Additionally, you must provide the outcomes sequentially "
                   f"(ie, outcome_one, then outcome_two, and then outcome_three, and then outcome_four.)")
            await ctx.send(content=msg, hidden=True)
            return

        if timeout_str is None:
            timeout = datetime.datetime.now() + datetime.timedelta(minutes=5)
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

        bet = self.user_bets.create_new_bet(
            ctx.guild.id,
            ctx.author.id,
            bet_title,
            options=list(option_dict.keys()),
            option_dict=option_dict,
            timeout=timeout
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

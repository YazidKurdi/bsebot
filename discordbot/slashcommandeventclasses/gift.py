import datetime

import discord

from discordbot.bot_enums import TransactionTypes, ActivityTypes
from discordbot.slashcommandeventclasses import BSEddies


class BSEddiesGift(BSEddies):
    """
    Class for handling `/bseddies gift` command
    """

    def __init__(self, client, guilds, logger):
        super().__init__(client, guilds, logger)

    async def gift_eddies(
        self, ctx: discord.ApplicationContext,
        friend: discord.User,
        amount: int
    ) -> None:
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
            msg = "You have insufficient points to perform that action."
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

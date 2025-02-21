
import discord

from discordbot.bot_enums import ActivityTypes
from discordbot.slashcommandeventclasses import BSEddies


class BSEddiesActive(BSEddies):
    """
    Class for handling `/active` commands
    """

    def __init__(self, client, guilds, logger):
        super().__init__(client, guilds, logger)

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

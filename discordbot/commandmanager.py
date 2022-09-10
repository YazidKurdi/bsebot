"""
This file contains our class that registers all the events we listen to and do things with
"""

import logging

from typing import Union

import discord
from discord import SlashCommand, SlashCommandGroup, SlashCommandOptionType

from apis.giphyapi import GiphyAPI
# from discordbot.betcloser import BetCloser
from discordbot.clienteventclasses import OnReadyEvent, OnReactionAdd, OnMessage, OnMemberJoin, OnDirectMessage
from discordbot.clienteventclasses import OnMemberLeave, OnReactionRemove, OnThreadCreate, OnThreadUpdate
# from discordbot.eddiegainmessageclass import EddieGainMessager
# from discordbot.eddiekingtask import BSEddiesKingTask
from discordbot.embedmanager import EmbedManager
# from discordbot.inactiveusertask import BSEddiesInactiveUsers
# from discordbot.loancollectiontask import BSEddiesLoanCollections
# from discordbot.revolutiontask import BSEddiesRevolutionTask
# from discordbot.serverinfotask import ServerInfo
from discordbot.slashcommandeventclasses import BSEddiesLeaderboard, BSEddiesView, BSEddiesActive, BSEddiesGift
from discordbot.slashcommandeventclasses import BSEddiesHighScore
from discordbot.slashcommandeventclasses import BSEddiesCreateBet, BSEddiesCloseBet, BSEddiesPlaceBet
from discordbot.slashcommandeventclasses import BSEddiesPending, BSEddiesTransactionHistory
# from discordbot.slashcommandeventclasses import BSEddiesLoanTake, BSEddiesLoanView, BSEddiesLoanRepay, BSEddiesAdminGive
# from discordbot.slashcommandeventclasses import BSEddiesAutoGeneratedBets, BSEddiesHighScore, BSEddiesAdminSwitch
from discordbot.slashcommandeventclasses import BSEddiesPredict  #, BSEddiesKing,
# from discordbot.slashcommandeventclasses import BSEServerTurnOff, BSEServerTurnOn, BSEToggleGameService
from discordbot.modals import BSEddiesBetCreateModal
from discordbot.views import PlaceABetView
from mongo.bsepoints import UserPoints, UserBets


class CommandManager(object):
    """
    Class for registering all the client events and slash commands
    Needs to be initialised with a client and a list of guild IDS

    Only the constructor needs to be called in this class for it to register everything.
    """

    def __init__(self,
                 client: discord.Bot,
                 guilds: list,
                 logger: logging.Logger,
                 beta_mode: bool = False,
                 debug_mode: bool = False,
                 giphy_token: str = None):
        """
        Constructor method. This does all the work in this class and no other methods need to be called.

        We start by creating all the variables we need and some also an EmbedManager class (for creating embeds),
        and our MongoDB Collection classes for interacting with those collections in the DB.

        This is also where we create an instance of "SlashCommand". This is our main class that handles registering
        of the slash commands.

        Each "event" or "slash command" has their own "class" that handles all the actual logic for when we receive
        an event or slash command. So we create instances of these classes next.

        We have the Client Event classes all being registered and then all the Slash Command events being registered.

        After that, we have our "tasks". Tasks are COG objects that perform a task at regular intervals. We use tasks
        for a variety of different things. But essentially, each one is a class and we create an instance of each one
        here. There's no need to do anything else once we instantiate each of them.

        And finally, we call the two methods that actually register all the events and slash commands.

        :param client: discord.Client object that represents our bot
        :param guilds: list of guild IDs that we're listening on
        :param logger:  logger object for logging
        :param beta_mode: whether we're in beta mode or not
        :param debug_mode: whether we're in debug mode or not
        :param giphy_token:
        """

        self.client = client
        self.beta_mode = beta_mode
        self.guilds = guilds
        self.logger = logger
        self.giphy_token = giphy_token

        self.embeds = EmbedManager(self.logger)

        self.giphyapi = GiphyAPI(self.giphy_token)

        # mongo interaction classes
        self.user_points = UserPoints()
        self.user_bets = UserBets(guilds)

        self.__get_cached_messages_list()

        # client event classes
        self.on_ready = OnReadyEvent(client, guilds, self.logger, self.beta_mode)
        self.on_reaction_add = OnReactionAdd(client, guilds, self.logger, self.beta_mode)
        self.on_reaction_remove = OnReactionRemove(client, guilds, self.logger, self.beta_mode)
        self.on_message = OnMessage(client, guilds, self.logger, self.beta_mode)
        self.on_member_join = OnMemberJoin(client, guilds, self.logger, self.beta_mode)
        self.on_member_leave = OnMemberLeave(client, guilds, self.logger, self.beta_mode)
        self.direct_message = OnDirectMessage(client, guilds, self.logger, self.giphyapi, self.beta_mode)
        self.on_thread_create = OnThreadCreate(client, guilds, self.logger, self.beta_mode)
        self.on_thread_update = OnThreadUpdate(client, guilds, self.logger, self.beta_mode)

        # slash command classes
        self.bseddies_active = BSEddiesActive(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_create = BSEddiesCreateBet(client, guilds, self.logger, self.beta_mode)
        self.bseddies_gift = BSEddiesGift(client, guilds, self.logger, self.beta_mode)
        self.bseddies_view = BSEddiesView(client, guilds, self.logger, self.beta_mode)
        self.bseddies_leaderboard = BSEddiesLeaderboard(client, guilds, self.logger, self.beta_mode)
        self.bseddies_close = BSEddiesCloseBet(client, guilds, self.logger, self.beta_mode)
        self.bseddies_place = BSEddiesPlaceBet(client, guilds, self.logger, self.beta_mode)
        self.bseddies_pending = BSEddiesPending(client, guilds, self.logger, self.beta_mode)
        self.bseddies_transactions = BSEddiesTransactionHistory(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_loan_take = BSEddiesLoanTake(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_loan_view = BSEddiesLoanView(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_loan_repay = BSEddiesLoanRepay(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_autogen = BSEddiesAutoGeneratedBets(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_admin_give = BSEddiesAdminGive(client, guilds, self.logger, self.beta_mode)
        self.bseddies_high_score = BSEddiesHighScore(client, guilds, self.logger, self.beta_mode)
        # self.bseddies_admin_switch = BSEddiesAdminSwitch(client, guilds, self.logger, self.beta_mode)
        self.bseddies_predict = BSEddiesPredict(client, guilds, self.logger, self.beta_mode)

        # tasks
        # self.bet_closer_task = BetCloser(self.client, guilds, self.logger)
        # self.eddie_gain_message_task = EddieGainMessager(self.client, guilds, self.logger)
        # self.eddie_king_task = BSEddiesKingTask(self.client, guilds, self.logger)
        # self.loan_collections = BSEddiesLoanCollections(self.client, guilds, self.logger)
        # self.inactive_users = BSEddiesInactiveUsers(self.client, guilds, self.logger)
        # self.revolution_task = BSEddiesRevolutionTask(self.client, guilds, self.logger, self.giphy_token)
        # self.server_info = ServerInfo(self.client, self.logger)

        # server slash commands
        # self.server_on = BSEServerTurnOn(client, guilds, logger, self.server_info)
        # self.server_off = BSEServerTurnOff(client, guilds, logger, self.server_info)
        # self.service_toggle = BSEToggleGameService(client, guilds, logger, self.server_info)

        # create all the subcommand groups
        self.bet_group = SlashCommandGroup("bet", "Bet related stuff")  # type: SlashCommandGroup

        # call the methods that register the events we're listening for
        self._register_client_events()
        self._register_slash_commands(guilds)

        self.client.add_application_command(self.bet_group)

    # noinspection PyProtectedMember
    def __get_cached_messages_list(self) -> list:
        """
        Method for getting a list of cached message IDs
        :return: list of cached messages
        """
        deque = self.client.cached_messages._SequenceProxy__proxied
        cached = [d.id for d in deque]
        return cached

    def _register_client_events(self) -> None:
        """
        This method registers all the 'client events'.
        Client Events are normal discord events that we can listen to.
        A full list of events can be found here: https://discordpy.readthedocs.io/en/latest/api.html

        Each event must be it's own async method with a @self.client.event decorator so that it's actually
        registered. None of these methods defined here will ever be called manually by anyone. The methods are called
        by the CLIENT object and that will pass in all the required parameters.

        Additionally, the method is called automatically from this class' constructor and shouldn't be called anywhere
        else.

        :return: None
        """

        @self.client.event
        async def on_ready():
            """
            Event that handles when we're 'ready'
            :return:
            """
            await self.on_ready.on_ready()

        @self.client.event
        async def on_member_join(member: discord.Member):
            """
            Event that's called when a new member joins the guild.
            :param member:
            :return:
            """
            self.on_member_join.on_join(member)

        @self.client.event
        async def on_member_remove(member: discord.Member):
            """
            Event that's called when a member leaves the guild.
            :param member:
            :return:
            """
            self.on_member_leave.on_leave(member)

        @self.client.event
        async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
            """
            This event catches EVERY reaction event on every message in the server.
            However, any operations we want to perform are a bit slower as we need to 'fetch' the message
            before we have all the data we have. BUT, we need to handle reactions to all messages as a user may
            react to an older message that isn't in the cache and we can't just not do anything.

            If the message is in the cache - then this event will fire and so will on_reaction_add. To prevent that,
            and to keep on_reaction_add for cached messages and be faster, we check if the message_id is already
            in the cache. If it is, then we can safely ignore it here. Otherwise we need to handle it.
            :param payload:
            :return:
            """

            cached_messages = self.__get_cached_messages_list()
            if payload.message_id in cached_messages:
                # message id is already in the cache
                return

            guild = self.client.get_guild(payload.guild_id)  # type: discord.Guild
            user = await self.client.fetch_user(payload.user_id)  # type: discord.User

            if user.bot:
                return

            channel = guild.get_channel(payload.channel_id)  # type: discord.TextChannel
            partial_message = channel.get_partial_message(payload.message_id)  # type: discord.PartialMessage
            message = await partial_message.fetch()  # type: discord.Message

            await self.on_reaction_add.handle_reaction_event(message, guild, channel, payload.emoji.name, user)

        @self.client.event
        async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
            """
            This event catches EVERY reaction removal event on every message in the server.
            However, any operations we want to perform are a bit slower as we need to 'fetch' the message
            before we have all the data we have. BUT, we need to handle reactions to all messages as a user may
            react to an older message that isn't in the cache and we can't just not do anything.

            If the message is in the cache - then this event will fire and so will on_reaction_add. To prevent that,
            and to keep on_reaction_add for cached messages and be faster, we check if the message_id is already
            in the cache. If it is, then we can safely ignore it here. Otherwise we need to handle it.
            :param payload:
            :return:
            """

            cached_messages = self.__get_cached_messages_list()
            if payload.message_id in cached_messages:
                # message id is already in the cache
                return

            guild = self.client.get_guild(payload.guild_id)  # type: discord.Guild
            user = await self.client.fetch_user(payload.user_id)  # type: discord.User

            if user.bot:
                return

            channel = guild.get_channel(payload.channel_id)  # type: discord.TextChannel
            partial_message = channel.get_partial_message(payload.message_id)  # type: discord.PartialMessage
            message = await partial_message.fetch()  # type: discord.Message

            await self.on_reaction_remove.handle_reaction_event(message, guild, channel, payload.emoji.name, user)

        @self.client.event
        async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
            """
            This event is triggered when anyone 'reacts' to a message in a guild that the bot is in - even it's own
            reactions. However, this only triggers for messages that the bot has in it's cache - reactions to older
            messages will only trigger a 'on_raw_reaction_add' event.

            Here, we simply hand it off to another class to deal with.
            :param reaction:
            :param user:
            :return:
            """
            await self.on_reaction_add.handle_reaction_event(
                reaction.message,
                reaction.message.guild,
                reaction.message.channel,
                reaction.emoji,
                user
            )

        @self.client.event
        async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):
            """
            This event is triggered when anyone removes a 'reaction' to a message in a guild that the bot is in -
            even it's own eactions. However, this only triggers for messages that the bot has in it's cache -
            reactions to older messages will only trigger a 'on_raw_reaction_remove' event.

            Here, we simply hand it off to another class to deal with.
            :param reaction:
            :param user:
            :return:
            """
            await self.on_reaction_remove.handle_reaction_event(
                reaction.message,
                reaction.message.guild,
                reaction.message.channel,
                reaction.emoji,
                user
            )

        @self.client.event
        async def on_thread_create(thread: discord.Thread):
            """

            :param thread:
            :return:
            """
            await self.on_thread_create.on_thread_create(thread)

        @self.client.event
        async def on_thread_update(before: discord.Thread, after: discord.Thread):
            """

            :param before:
            :param after:
            :return:
            """

            await self.on_thread_update.on_update(before, after)

        @self.client.event
        async def on_message(message: discord.Message):
            """
            This is the 'message' event. Whenever a message is sent in a guild that the bot is listening for -
            we will enact this code. Here, we simply hand it off to another class to deal with.
            :param message:
            :return:
            """

            if message.author.bot:
                return

            if message.channel.type.value == 1:
                # this means we've received a Direct message!
                # we'll have to handle this differently
                self.logger.debug(f"{message} - {message.content}")
                await self.direct_message.dm_received(message)
                return

            await self.on_message.message_received(message)

    def _register_slash_commands(self, guilds: list) -> None:
        """
        This method registers all the 'slash commands'.
        Slash Commands are commands users can use in discord.

        Each command must be it's own async method with a relevant decorator so that it's actually
        registered. None of these methods defined here will ever be called manually by anyone. The methods are called
        by the CLIENT object and that will pass in all the required parameters.

        Additionally, the method is called automatically from this class' constructor and shouldn't be called anywhere
        else.

        :param guilds: The guild IDs to register the commands to
        :return: None
        """

        @self.client.command(description="View your total BSEddies")
        async def view(ctx: discord.ApplicationContext) -> None:
            """
            Slash command that allows the user to see how many BSEddies they have.
            :param ctx:
            :return:
            """
            await self.bseddies_view.view(ctx)

        @self.client.command(description="View the current BSEddies leaderboard")
        async def leaderboard(ctx: discord.ApplicationContext) -> None:
            """
            Slash command that allows the user to see the BSEddies leaderboard.
            :param ctx:
            :return:
            """
            await self.bseddies_leaderboard.leaderboard(ctx)

        @self.client.command(description="See your estimated salary gain for today so far")
        async def predict(ctx: discord.ApplicationContext) -> None:
            """
            Slash command that allows the user to see their predict daily salary.
            :param ctx:
            :return:
            """
            await self.bseddies_predict.predict(ctx)

        @self.client.command(description="View the BSEddies High Scores.")
        async def highscores(ctx: discord.ApplicationContext) -> None:
            """
            Slash command that allows the user to see the BSEddies high scores.
            :param ctx:
            :return:
            """
            await self.bseddies_high_score.highscore(ctx)

        @self.client.command(description="View all the active bets in the server.")
        async def active(ctx: discord.ApplicationContext) -> None:
            """
            Slash commands lists all the active bets in the system.
            :param ctx:
            :return:
            """
            await self.bseddies_active.active(ctx)

        @self.client.command(description="View all the unresolved bets you have betted on.")
        async def pending(ctx: discord.ApplicationContext) -> None:
            """
            Slash commands lists all the pending bets in the system for the user.
            :param ctx:
            :return:
            """
            await self.bseddies_pending.pending(ctx)

        @self.client.command(description="Gift some of your eddies to a friend")
        async def gift(
                ctx: discord.ApplicationContext,
                friend: discord.Option(discord.User),
                amount: discord.Option(int)) -> None:
            """
            A slash command that allows users to gift eddies to their friends.

            It was two main arguments:
                - FRIEND: The user in the server to gift BSEddies to
                - AMOUNT: The amount of BSEddies to gift

            :param ctx:
            :param friend:
            :param amount:
            :return:
            """
            await self.bseddies_gift.gift_eddies(ctx, friend, amount)

        @self.client.command(description="View your transaction history.")
        async def transactions(
                ctx: discord.ApplicationContext,
                full: discord.Option(bool, description="Do you want the full transaction history?", default=False),
        ) -> None:
            """
            Slash command that allows the user to see their eddie transaction history
            :param ctx:
            :param full:
            :return:
            """
            await ctx.defer(ephemeral=True)
            await self.bseddies_transactions.transaction_history(ctx, full)

        @self.client.command(description="Create a bet")
        async def create(ctx: discord.ApplicationContext):
            modal = BSEddiesBetCreateModal(
                client=self.client,
                guilds=self.guilds,
                logger=self.logger,
                beta=self.beta_mode,
                title="Create a bet"
            )
            await ctx.send_modal(modal)

        @self.client.command(description="Place a bet")
        async def place(ctx: discord.ApplicationContext) -> None:
            """
            This is the command that allows users to place BSEddies.  on currently active bets.

            It has 3 main arguments:
                - BET_ID : The ID of the bet
                - AMOUNT : The amount of BSEddies to bet
                - EMOJI : The result to bet on

            Users can only bet on "active" bets. IE ones that haven't timed out or ones that have results already.
            Users can't bet on a different result to one that they've already bet on.
            Users can't bet a negative amount of BSEddies.
            Users can't bet on a result that doesn't exist for that bet.

            :param ctx:
            :return:
            """
            await self.bseddies_place.create_bet_view(ctx)

        @self.client.command(description="Close a bet by providing a result and award those SWEET EDDIES.")
        async def close(ctx: discord.ApplicationContext) -> None:
            """
            This is the command that closes a bet. Closing a bet requires a result emoji.
            Once a bet is "closed" - no-one can bet on it and the winners will gain their BSEddies.

            :param ctx:
            :return:
            """
            await self.bseddies_close.create_bet_view(ctx)

        return

        @self.slash.subcommand(
            base="bseddies",
            base_description="View your BSEddies, create bets and resolve bets",
            subcommand_group="bet",
            subcommand_group_description="Create, resolve, or place bets using BSEddies",
            name="autogenerate",
            description="Autogenerate a random selection of bets for a specified scenario",
            options=[
                manage_commands.create_option(
                    name="scenario_type",
                    description="Which scenario are we creating bets for?",
                    option_type=3,
                    required=True,
                    choices=[
                        manage_commands.create_choice("valorant", "Valorant"),
                        manage_commands.create_choice("pook", "Pook")
                    ]
                ),
                manage_commands.create_option(
                    name="timeout",
                    description=("How long should betting be open for? Must be DIGITS + (s|m|h|d). "
                                 "Examples: 15m, 2d, 6h, etc"),
                    option_type=3,
                    required=False
                )
            ],
            guild_ids=guilds
        )
        async def autogenerate_bets(
                ctx: discord.ApplicationContext,
                scenario_type: str,
                timeout: str,
        ) -> None:
            """

            :param ctx:
            :param scenario_type:
            :param timeout:
            :return:
            """
            await ctx.defer(hidden=True)
            await self.bseddies_autogen.generate_bets(ctx, scenario_type, timeout)

        @self.slash.subcommand(
            base="bseddies",
            base_description="View your BSEddies, create bets and resolve bets",
            subcommand_group="admin",
            subcommand_group_description="Admin commands for the admin",
            name="give",
            description="Give a user some eddies",
            options=[
                manage_commands.create_option(
                    name="user",
                    description="The user to give eddies to",
                    option_type=6,
                    required=True,
                ),
                manage_commands.create_option(
                    name="amount",
                    description="Amount of eddies to give them",
                    option_type=4,
                    required=True,
                ),
            ],
            guild_ids=guilds
        )
        async def admin_give_user_eddies(
                ctx: discord.ApplicationContext, user: discord.User, amount: int) -> None:
            """
            Slash command for an admin to give eddies for someone.
            :param ctx:
            :param user:
            :param amount:
            :return:
            """
            await self.bseddies_admin_give.admin_give(ctx, user, amount)

        @self.slash.subcommand(
            base="bseddies",
            base_description="View your BSEddies, create bets and resolve bets",
            subcommand_group="admin",
            subcommand_group_description="Admin commands for the admin",
            name="switch",
            description="Switch a user's bet on a given bet",
            options=[
                manage_commands.create_option(
                    name="user",
                    description="The user to switch result for",
                    option_type=6,
                    required=True,
                ),
                manage_commands.create_option(
                    name="bet_id",
                    description="The BET ID to switch the result on",
                    option_type=3,
                    required=True,
                ),
                manage_commands.create_option(
                    name="emoji",
                    description="The new result",
                    option_type=3,
                    required=True,
                ),
            ],
            guild_ids=guilds
        )
        async def admin_give_user_eddies(
                ctx: discord.ApplicationContext, user: discord.User, bet_id: str, emoji: str) -> None:
            """
            Slash command for an admin to switch a user's bet on a given bet.
            :param ctx:
            :param user:
            :param bet_id:
            :param emoji:
            :return:
            """
            await self.bseddies_admin_switch.admin_switch(ctx, user, bet_id, emoji)

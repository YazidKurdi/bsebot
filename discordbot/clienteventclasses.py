import datetime
import discord
import re

from discord.emoji import Emoji

from discordbot.baseeventclass import BaseEvent
from discordbot.bot_enums import TransactionTypes, ActivityTypes
from discordbot.constants import THE_BOYS_ROLE
from discordbot.reactioneventclasses import BetReactionEvent, LeaderBoardReactionEvent, RevolutionReactionEvent
from discordbot.reactioneventclasses import HighScoreReactionEvent
from mongo.bsepoints import UserInteractions


class OnReadyEvent(BaseEvent):
    """
    Class for handling on_ready event
    """
    def __init__(self, client: discord.Bot, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)

    async def on_ready(self) -> None:
        """
        Method called for on_ready event. Makes sure we have an entry for every user in each guild.
        :return: None
        """
        self.logger.info("Checking guilds for members")

        for guild_id in self.guild_ids:
            guild = self.client.get_guild(guild_id)  # type: discord.Guild
            self.logger.info(f"Checking guild: {guild.id} - {guild.name}")
            for member in guild.members:  # type: discord.Member
                if member.bot:
                    continue

                self.logger.info(f"Checking {member.id} - {member.name}")
                user = self.user_points.find_user(member.id, guild.id)
                if not user:

                    the_boys_role = [role for role in member.roles if role == THE_BOYS_ROLE]

                    self.user_points.create_user(member.id, guild.id, bool(the_boys_role))
                    self.logger.info(
                        f"Creating new user entry for {member.id} - {member.name} for {guild.id} - {guild.name}"
                    )

                    self.user_points.append_to_transaction_history(
                        member.id,
                        guild.id,
                        {
                            "type": TransactionTypes.USER_CREATE,
                            "amount": 10,
                            "timestamp": datetime.datetime.now(),
                            "comment": "User created",
                        }
                    )
                    continue

                if not user.get("daily_eddies"):
                    the_boys_role = [role for role in member.roles if role == THE_BOYS_ROLE]
                    self.user_points.set_daily_eddies_toggle(member.id, guild.id, bool(the_boys_role))

            await guild.fetch_emojis()
            # sort out emojis
            emojis_list = []
            for emoji in guild.emojis:
                emoji_obj = await guild.fetch_emoji(emoji.id)
                print(f"{emoji_obj.user}: {emoji_obj.name}")

            # join all threads
            for channel in guild.channels:
                if type(channel) not in [discord.channel.TextChannel]:
                    continue

                if threads := channel.threads:
                    for thread in threads:
                        if thread.archived or thread.locked:
                            continue

                        await thread.fetch_members()

                        if self.client.user.id not in [member.id for member in thread.members]:
                            await thread.join()
                            print(f"Joined {thread.name}")

        self.logger.info("Finished member check.")


class OnMemberJoin(BaseEvent):
    """
    Class for handling when a new member joins the server
    """
    def __init__(self, client, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)

    def on_join(self, member: discord.Member) -> None:
        """
        Method for handling when a new member joins the server.
        We basically just make sure that the user has an entry in our DB
        :param member:
        :return: None
        """
        user_id = member.id

        if user := self.user_points.find_user(user_id, member.guild.id):
            self.user_points.update({"_id": user["_id"]}, {"$set": {"inactive": False}})
            self.logger.info(f"Activating BSEddies account for existing user - {user_id} - {member.display_name}")
            self.user_points.append_to_activity_history(
                user_id,
                member.guild.id,
                {
                    "type": ActivityTypes.SERVER_JOIN,
                    "timestamp": datetime.datetime.now()
                }
            )
            return

        self.user_points.create_user(user_id, member.guild.id)

        self.user_points.append_to_transaction_history(
            user_id,
            member.guild.id,
            {
                "type": TransactionTypes.USER_CREATE,
                "amount": 10,
                "timestamp": datetime.datetime.now(),
                "comment": "User created",
            }
        )

        self.user_points.append_to_activity_history(
            user_id,
            member.guild.id,
            {
                "type": ActivityTypes.SERVER_JOIN,
                "timestamp": datetime.datetime.now()
            }
        )

        self.logger.info(f"Creating BSEddies account for new user - {user_id} - {member.display_name}")


class OnMemberLeave(BaseEvent):
    """
    Class for handling when a member leaves the server
    """
    def __init__(self, client, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)

    def on_leave(self, member: discord.Member) -> None:
        """
        Method for handling when a member leaves the server.
        We basically just make sure that the user entry is set to inactive
        :param member:
        :return: None
        """
        user_id = member.id
        self.user_points.update({"uid": user_id, "guild_id": member.guild.id}, {"$set": {"inactive": True}})
        self.user_points.append_to_activity_history(
            user_id,
            member.guild.id,
            {
                "type": ActivityTypes.SERVER_LEAVE,
                "timestamp": datetime.datetime.now()
            }
        )
        self.logger.info(f"Deactivating BSEddies account for user - {user_id} - {member.display_name}")
        return


class OnReactionAdd(BaseEvent):
    """
    Class for handling on_reaction_add events from Discord
    """
    def __init__(self, client, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)
        self.user_interactions = UserInteractions()
        self.leadership_event = LeaderBoardReactionEvent(client, guild_ids, logger, beta_mode=beta_mode)
        self.high_score_event = HighScoreReactionEvent(client, guild_ids, logger, beta_mode=beta_mode)
        self.bet_event = BetReactionEvent(client, guild_ids, logger, beta_mode=beta_mode)
        self.revolution_event = RevolutionReactionEvent(client, guild_ids, logger, beta_mode=beta_mode)

    async def handle_reaction_event(
            self,
            message: discord.Message,
            guild: discord.Guild,
            channel: discord.TextChannel,
            reaction_emoji: str,
            user: discord.User
    ) -> None:
        """
        Main event for handling reaction events.

        Firstly, we only care about reactions if they're from users so we discard any bot reactions.

        Secondly, we work out if it's a reaction to a user message or a bot message and handle accordingly.

        Then we check what type of message the user is reacting to and pass it off to the relevant class to handle
        the event

        :param message:
        :param guild:
        :param channel:
        :param reaction_emoji:
        :param user:
        :return:
        """
        if user.bot:
            return

        if guild.id not in self.guild_ids:
            return

        if not message.author.bot:
            self.handle_user_reaction(reaction_emoji, message, guild, channel, user, message.author)
            return

        # handling leaderboard messages
        if message.content and "BSEddies Leaderboard" in message.content and reaction_emoji == u"▶️":
            await self.leadership_event.handle_leaderboard_reaction(message, guild)
            return

        # handle high score messages
        if message.content and "BSEddies High Scores" in message.content and reaction_emoji == u"▶️":
            await self.high_score_event.handle_highscore_reaction(message, guild)
            return

        # handling reactions to BETS
        if message.embeds and "Bet ID" in message.embeds[0].description:
            await self.bet_event.handle_bet_reaction_event(message, guild, channel, reaction_emoji, user)
            return

        # handling reactions to REVOLUTIONS
        if message.content and "REVOLUTION IS UPON US" in message.content and reaction_emoji == "🎟️":
            await self.revolution_event.handle_revolution_reaction(message, guild, user)

    def handle_user_reaction(
            self, reaction: str, message: discord.Message,
            guild: discord.Guild, channel: discord.TextChannel, user: discord.User, author: discord.Member
    ) -> None:
        """

        :param reaction:
        :param message:
        :param guild:
        :param channel:
        :param user:
        :param author:
        :return:
        """
        message_id = message.id
        guild_id = guild.id

        if isinstance(reaction, (Emoji, discord.PartialEmoji)):
            reaction = reaction.name

        self.user_interactions.add_reaction_entry(
            message_id,
            guild_id,
            user.id,
            channel.id,
            reaction,
            message.created_at,
            author.id
        )


class OnReactionRemove(BaseEvent):
    """
    Class for handling on_reaction_remove events from Discord
    """
    def __init__(self, client, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)
        self.user_interactions = UserInteractions()

    async def handle_reaction_event(
            self,
            message: discord.Message,
            guild: discord.Guild,
            channel: discord.TextChannel,
            reaction_emoji: str,
            user: discord.User
    ) -> None:
        """
        Main event for handling reaction events.

        Firstly, we only care about reaction removals if they're from users so we discard any bot reactions.

        Secondly, we only care about reaction removals to user messages at the moment so discard any other events.

        Then we check what type of message the user is reacting to and pass it off to the relevant class to handle
        the event

        :param message:
        :param guild:
        :param channel:
        :param reaction_emoji:
        :param user:
        :return:
        """
        if user.bot:
            return

        if guild.id not in self.guild_ids:
            return

        if not message.author.bot:
            self.handle_user_reaction(reaction_emoji, message, guild, channel, user, message.author)
            return

    def handle_user_reaction(
            self, reaction: str, message: discord.Message,
            guild: discord.Guild, channel: discord.TextChannel, user: discord.User, author: discord.Member
    ) -> None:
        """

        :param reaction:
        :param message:
        :param guild:
        :param channel:
        :param user:
        :param author:
        :return:
        """
        message_id = message.id
        guild_id = guild.id

        self.user_interactions.remove_reaction_entry(
            message.id,
            guild_id,
            user.id,
            channel.id,
            reaction,
            message.created_at,
            author.id
        )


class OnMessage(BaseEvent):
    """
    Class for handling on_message events from Discord
    """

    def __init__(self, client, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)
        self.user_interactions = UserInteractions()

    async def message_received(self, message: discord.Message, message_type_only=False):
        """
        Main method for handling when we receive a message.
        Mostly just extracts data and puts it into the DB.
        We also work out what "type" of message it is.
        :param message:
        :param message_type_only:
        :return:
        """

        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id
        message_content = message.content

        if guild_id not in self.guild_ids:
            return

        message_type = []

        if message.reference:
            referenced_message = self.client.get_message(message.reference.message_id)  # type: discord.Message
            if not referenced_message:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message.author.id != user_id:
                message_type.append("reply")
                self.user_interactions.add_reply_to_message(
                    message.reference.message_id, message.id, guild_id, user_id, message.created_at, message_content
                )

        if message.attachments:
            message_type.append("attachment")

        if role_mentions := message.role_mentions:
            for _ in role_mentions:
                message_type.append("role_mention")

        if channel_mentions := message.channel_mentions:
            for _ in channel_mentions:
                message_type.append("channel_mention")

        if mentions := message.mentions:
            for mention in mentions:
                if mention.id == user_id:
                    continue
                message_type.append("mention")

        if message.mention_everyone:
            message_type.append("everyone_mention")

        if "https://" in message.content or "http://" in message_content:
            if "gif" in message.content:
                message_type.append("gif")
            else:
                message_type.append("link")

        if not message.attachments:
            message_type.append("message")

        if re.match("Wordle \d?\d\d\d \d\/\d\\n\\n", message.content):
            message_type.append("wordle")

        if message_type_only:
            return message_type

        self.user_interactions.add_entry(
            message.id,
            guild_id,
            user_id,
            channel_id,
            message_type,
            message_content,
            message.created_at
        )


class OnDirectMessage(BaseEvent):
    """
    Class for handling on_message events from Discord
    """

    def __init__(self, client, guild_ids, logger, giphyapi, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)
        self.giphyapi = giphyapi

        self.thanks = ["thank you", "thanks", "fanks", "fank you", " ty ", "thanks dad"]
        self.rude = ["fuck you", "fuck off", "faggot", "fuckyou"]

    async def dm_received(self, message: discord.Message):
        """
        Main method for handling when someone sends us a DM
        Basically, send a random gif if they say 'thank you'
        :param message:
        :return:
        """
        message_content = message.content

        if [a for a in self.thanks if a in message_content.lower()]:
            gif = await self.giphyapi.random_gif("youre welcome")
            await message.author.send(content=gif)
        elif [a for a in self.rude if a in message_content.lower()]:
            gif = await self.giphyapi.random_gif("shocked")
            await message.author.send(content=gif)


class OnThreadCreate(BaseEvent):
    """
        Class for handling on_thread_create event
        """

    def __init__(self, client: discord.Bot, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)
        self.user_interactions = UserInteractions()
        self.on_message = OnMessage(client, guild_ids, logger, beta_mode)

    async def on_thread_create(self, thread: discord.Thread) -> None:
        """
        Method called for on_ready event. Makes sure we have an entry for every user in each guild.
        :return: None
        """
        await thread.join()
        print(f"Joined {thread.name}")

        if not thread.starting_message:
            starting_message = await thread.fetch_message(thread.id)  # type: discord.Message
        else:
            starting_message = thread.starting_message  # type: discord.Message

        message_type = await self.on_message.message_received(starting_message, True)
        message_type.extend("thread_create")

        self.user_interactions.add_entry(
            thread.id,
            thread.guild.id,
            thread.owner_id,
            thread.parent_id,
            message_type,
            starting_message.content,
            thread.created_at
        )


class OnThreadUpdate(BaseEvent):
    """
    Class for handling on_thread_update event
    """

    def __init__(self, client: discord.Bot, guild_ids, logger, beta_mode=False):
        super().__init__(client, guild_ids, logger, beta_mode=beta_mode)

    async def on_update(self, before: discord.Thread, after: discord.Thread):
        """

        :param before:
        :param after:
        :return:
        """
        if before.archived and not after.archived:
            print(f"Thread has been unarchived - joining")
            thread_members = await after.fetch_members()
            member_ids = [member.id for member in thread_members]
            if self.client.user.id not in member_ids:
                await after.join()
                print(f"Joining unarchived thread")

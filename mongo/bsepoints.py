"""
This is a file for Collection Classes in a MongoDB database.

A MongoDB database can have lots of Collections (basically tables). Each Collection should have a class here
that provides methods for interacting with that Collection.

This particular file contains Collection Classes for the 'bestsummereverpoints' DB.
"""

import datetime
from typing import Union

from pymongo.results import UpdateResult

from discordbot.bot_enums import TransactionTypes
from mongo import interface
from mongo.db_classes import BestSummerEverPointsDB


class UserPoints(BestSummerEverPointsDB):
    """
    Class for interacting with the 'userpoints' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "userpoints")

    def find_user(self, user_id: int, guild_id: int) -> Union[dict, None]:
        """
        Looks up a user in the collection.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :return: either a user dict or None if the user couldn't be found
        """
        ret = self.query({"uid": user_id, "guild_id": guild_id})
        if ret:
            return ret[0]
        return None

    def get_user_points(self, user_id: int, guild_id: int) -> int:
        """
        Returns a users points from a given guild.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :return: int - number of points the user has
        """
        ret = self.query({"uid": user_id, "guild_id": guild_id}, projection={"points": True})
        return ret[0]["points"]

    def get_user_daily_minimum(self, user_id: int, guild_id: int) -> int:
        """
        Returns the user's daily minimum points.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :return: int - user's 'daily minimum'
        """
        ret = self.query({"uid": user_id, "guild_id": guild_id}, projection={"daily_minimum": True})
        return ret[0]["daily_minimum"]

    def get_all_users_for_guild(self, guild_id: int) -> list:
        """
        Gets all the users from a given guild.

        :param guild_id: int - The guild ID to get users for
        :return: list of user dictionaries
        """
        ret = self.query({"guild_id": guild_id}, projection={"points": True, "uid": True, "daily_minimum": True})
        return ret

    def set_points(self, user_id: int, guild_id: int, points: int) -> UpdateResult:
        """
        Sets a user's points to a given value.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param points: int - points to set the user to
        :return: UpdateResults object
        """
        return self.update({"uid": user_id, "guild_id": guild_id}, {"$set": {"points": points}})

    def set_pending_points(self, user_id: int, guild_id: int, points: int) -> UpdateResult:
        """
        Sets a user's pending points to a given value.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param points: int - points to set the user's pending value to
        :return: UpdateResults object
        """
        return self.update({"uid": user_id, "guild_id": guild_id}, {"$set": {"pending_points": points}})

    def set_daily_minimum(self, user_id, guild_id, points) -> UpdateResult:
        """
        Sets the user's daily minimum points to a given value.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param points: int - points to set the user's daily minimum to
        :return: UpdateResults object
        """
        return self.update({"uid": user_id, "guild_id": guild_id}, {"$set": {"daily_minimum": points}})

    def increment_pending_points(self, user_id: int, guild_id: int, amount: int) -> UpdateResult:
        """
        Increases the 'pending' points of specified user

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param amount: int - amount to increase pending points by
        :return: UpdateResults object
        """
        return self.update({"uid": user_id, "guild_id": guild_id}, {"$inc": {"pending_points": amount}})

    def increment_points(self, user_id: int, guild_id: int, amount: int) -> UpdateResult:
        """
        Increases a user's points by a set amount.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param amount: int - amount to increase pending points by
        :return: UpdateResults object
        """
        return self.update({"uid": user_id, "guild_id": guild_id}, {"$inc": {"points": amount}})

    def increment_daily_minimum(self, user_id: int, guild_id: int, amount: int) -> UpdateResult:
        """
        Increments the user's daily minimum points by a given value.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param amount: int - amount to increase daily minimum by
        :return: UpdateResults object
        """
        return self.update({"uid": user_id, "guild_id": guild_id}, {"$inc": {"daily_minimum": amount}})

    def decrement_pending_points(self, user_id: int, guild_id: int, amount: int) -> UpdateResult:
        """
        Decreases a user's pending points by a set amount.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param amount: int - amount to decrease pending points by
        :return: UpdateResults object
        """
        return self.increment_pending_points(user_id, guild_id, amount * -1)

    def decrement_points(self, user_id: int, guild_id: int, amount: int) -> UpdateResult:
        """
        Decreases a user's points by a set amount.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param amount: int - amount to decrease points by
        :return: UpdateResults object
        """
        return self.increment_points(user_id, guild_id, amount * -1)

    def decrement_daily_minimum(self, user_id: int, guild_id: int, amount: int) -> UpdateResult:
        """
        Decreases a user's daily minimum points by set amount

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param amount: int - amount to decrease daily minimum
        :return: UpdateResults object
        """
        return self.increment_daily_minimum(user_id, guild_id, amount * -1)

    def create_user(self, user_id: int, guild_id: int) -> None:
        """
        Create basic user points document.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :return: None
        """
        user_doc = {
            "uid": user_id,
            "guild_id": guild_id,
            "points": 10,
            "pending_points": 0,
            "daily_minimum": 5,
            "transaction_history": [],
        }
        self.insert(user_doc)

    def append_to_transaction_history(self, user_id: int, guild_id: int, activity: dict) -> None:
        """
        Add an item to a user's transaction history

        Activity must be in the format:
        {
            'type': TRANSACTION_TYPE
            'amount': AMOUNT OF EDDIES GAINED/LOST (this should be positive for gain / negative for loss)
            'bet_id': OPTIONAL. Bet ID of bet user gained/lost eddies on
            'user_id': OPTIONAL. User ID user gave/received eddies to/from
            'timestamp': DATETIME OBJECT FOR TIMESTAMP
            'comment': OPTIONAL. Comment as to what happened
        }

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :param activity: the activity dict to add to the transaction history
        :return: None
        """
        self.update({"uid": user_id, "guild_id": guild_id}, {"$push": {"transaction_history": activity}})

    def append_to_activity_history(self, user_id: int, guild_id: int, activity: dict) -> None:
        """
        Add an item to a user's activity history

        Activity must be in the format:
        {
            'type': ACTIVITY_TYPE,
            'timestamp': DATETIME OBJECT FOR TIMESTAMP
            'comment': OPTIONAL. Comment as to what happened
        }

        :param user_id:
        :param guild_id:
        :param activity:
        :return:
        """
        self.update({"uid": user_id, "guild_id": guild_id}, {"$push": {"activity_history": activity}})


class UserBets(BestSummerEverPointsDB):
    """
    Class for interacting with the 'userbets' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self, guilds: list = None):
        """
        Constructor method. We initialise the collection object and also the UserPoints instance we need

        If we are given a list of guilds - then we make sure we have a bet counter object for that guild ID

        :param guilds: list of guild IDs
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "userbets")

        self.user_points = UserPoints()

        if guilds is None:
            guilds = []
        for guild in guilds:
            self.__create_counter_document(guild)

    def __create_counter_document(self, guild_id: int) -> None:
        """
        Method that creates our base 'counter' document for counting bet IDs

        :param guild_id: int - guild ID to create document for
        :return: None
        """
        if not self.query({"type": "counter", "guild_id": guild_id}):
            self.insert({"type": "counter", "guild_id": guild_id, "count": 1})

    def __get_new_bet_id(self, guild_id) -> str:
        """
        Generate new unique ID and return it in the format we want.

        :param guild_id: int - guild ID to create the new unique bet ID for
        :return: str - new unique bet ID
        """
        count = self.query({"type": "counter", "guild_id": guild_id}, projection={"count": True})[0]["count"]
        self.update({"type": "counter", "guild_id": guild_id}, {"$inc": {"count": 1}})
        return f"{count:04d}"

    def get_all_active_bets(self, guild_id: int) -> list:
        """
        Gets all active bets.

        :param guild_id: int - guild ID to get the active bets for
        :return: list of active bets
        """
        bets = self.query({"active": True, "guild_id": guild_id})
        return bets

    def get_all_pending_bets(self, guild_id: int) -> list:
        """
        Gets all 'pending' bets - bets that don't have a result yet.
        Could be active or closed.

        :param guild_id: int - guild ID to get the pending bets for
        :return: list of pending bets
        """
        bets = self.query({"result": None, "guild_id": guild_id})
        return bets

    def get_user_pending_points(self, user_id: int, guild_id: int) -> int:
        """
        Returns a users points from a given guild.

        We search for all the non-closed bets in the DB and get the points directly from there.

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :return: int - amount of pending points the user has
        """
        pending = 0

        pending_bets = self.query({f"betters.{user_id}": {"$exists": True}, "guild_id": guild_id, "result": None}, )
        for bet in pending_bets:
            our_user = bet["betters"][str(user_id)]
            pending += our_user["points"]

        return pending

    def get_all_pending_bets_for_user(self, user_id: int, guild_id: int) -> list:
        """
        Gets all pending bets for a given user_id

        :param user_id: int - The ID of the user to look for
        :param guild_id: int - The guild ID that the user belongs in
        :return: a list of bet dictionaries
        """
        pending_bets = self.query({f"betters.{user_id}": {"$exists": True}, "guild_id": guild_id, "result": None})
        return pending_bets

    def create_new_bet(self,
                       guild_id: int,
                       user_id: int,
                       title: str,
                       options: list,
                       option_dict: dict,
                       timeout: Union[datetime.datetime, None] = None,
                       private: bool = False) -> dict:
        """
        Creates a new bet and inserts it into the DB.

        :param private:
        :param guild_id: The guild ID to create the bet in
        :param user_id: The user ID that is creating the bet
        :param title: The title of the bet
        :param options: A list of the emoji options
        :param option_dict: A dictionary that has a bit more information about the available options for the bet
        :param timeout: A datetime object for when the bet will be 'closed'
        :return: A bet dictionary
        """

        bet_id = self.__get_new_bet_id(guild_id)
        bet_doc = {
            "bet_id": bet_id,
            "guild_id": guild_id,
            "user": user_id,
            "title": title,
            "options": options,
            "created": datetime.datetime.now(),
            "timeout": timeout,
            "active": True,
            "betters": {},
            "result": None,
            "option_dict": option_dict,
            "channel_id": None,
            "message_id": None,
            "private": private,
        }
        self.insert(bet_doc)
        return bet_doc

    def get_bet_from_id(self, guild_id: int, bet_id: int) -> Union[dict, None]:
        """
        Gets an already created bet document from the database.

        :param guild_id: int - The guild ID the bet exists in
        :param bet_id: int - The ID of the bet to get
        :return: a dict of the bet or None if there's no matching bet ID
        """

        ret = self.query({"bet_id": bet_id, "guild_id": guild_id})
        if ret:
            return ret[0]
        return None

    def add_better_to_bet(
            self,
            bet_id: int,
            guild_id: int,
            user_id: int,
            emoji: str,
            points: int) -> dict:
        """
        Logic for adding a 'better' to a bet.
        If the user is betting on this for the first time - we simply add the details to the DB
        If not, we check that the user has enough points, that they're betting on an option they have
        already bet on and if the bet is still active.

        :param bet_id: int - The ID of the bet to get
        :param guild_id: int - The guild ID the bet exists in
        :param user_id: int - the user ID of the user betting
        :param emoji: : str - the option the user is attempting to bet on
        :param points: int - the amount of points the user is betting
        :return: success dict
        """

        ret = self.query({"bet_id": bet_id, "guild_id": guild_id})[0]
        betters = ret["betters"]

        # this section is the logic if the user hasn't bet on this bet yet
        if str(user_id) not in betters:
            doc = {
                "user_id": user_id,
                "emoji": emoji,
                "first_bet": datetime.datetime.now(),
                "last_bet": datetime.datetime.now(),
                "points": points,
            }
            self.update({"_id": ret["_id"]}, {"$set": {f"betters.{user_id}": doc}})
            self.user_points.decrement_points(user_id, guild_id, points)
            return {"success": True}

        # here we're checking if the user has already bet on the option they have selected
        # if they haven't - then it's an error
        current_better = betters[str(user_id)]
        if emoji != current_better["emoji"]:
            return {"success": False, "reason": "wrong option"}

        # checking the user has enough points
        cur_points = self.user_points.get_user_points(user_id, guild_id)
        if (points > cur_points) or cur_points == 0:
            return {"success": False, "reason": "not enough points"}

        self.update(
            {"_id": ret["_id"]},
            {"$inc": {f"betters.{user_id}.points": points}, "$set": {"last_bet": datetime.datetime.now()}}
        )

        self.user_points.decrement_points(user_id, guild_id, points)
        new_points = self.user_points.get_user_points(user_id, guild_id)

        if new_points < 0:
            # transaction went wrong somewhere. Reverse all the transactions that we did
            # think this is a case of the user using reactions too quickly
            self.user_points.increment_points(user_id, guild_id, points)
            self.update(
                {"_id": ret["_id"]},
                {"$inc": {f"betters.{user_id}.points": -1 * points}, "$set": {"last_bet": datetime.datetime.now()}}
            )
            return {"success": False, "reason": "not enough points"}

        return {"success": True}

    def close_a_bet(self, bet_id: int, guild_id: int, emoji: str) -> dict:
        """
        Close a bet from a bet ID.
        Here we also calculate who the winners are and allocate their winnings to them.

        :param bet_id: str - the bet to close
        :param guild_id: int - the guild ID the bet resides in
        :param emoji: str - the winning result of the bet
        :return: a result_dict that has some info about the winners and losers
        """

        ret = self.query({"bet_id": bet_id, "guild_id": guild_id})[0]

        self.update(
            {"_id": ret["_id"]},
            {"$set": {"active": False, "result": emoji, "closed": datetime.datetime.now()}}
        )

        ret_dict = {
            "result": emoji,
            "outcome_name": ret["option_dict"][emoji],
            "timestamp": datetime.datetime.now(),
            "losers": {b: ret["betters"][b]["points"]
                       for b in ret["betters"] if ret["betters"][b]["emoji"] != emoji},
            "winners": {}
        }

        # assign winning points to the users who got the answer right
        for better in [b for b in ret["betters"] if ret["betters"][b]["emoji"] == emoji]:
            points_bet = ret["betters"][better]["points"]
            points_won = points_bet * 2
            ret_dict["winners"][better] = points_won
            self.user_points.increment_points(int(better), guild_id, points_won)
            # add to transaction history
            self.user_points.append_to_transaction_history(
                int(better),
                guild_id,
                {
                    "type": TransactionTypes.BET_WIN,
                    "amount": points_won,
                    "timestamp": datetime.datetime.now(),
                    "bet_id": bet_id,
                }
            )

        return ret_dict


class UserInteractions(BestSummerEverPointsDB):
    """
    Class for interacting with the 'userinteractions' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self):
        """
        Constructor method for the class. Initialises the collection object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "userinteractions")

    def add_entry(
            self,
            message_id: int,
            guild_id: int,
            user_id: int,
            channel_id: int,
            message_type: str,
            message_content: str,
            timestamp: datetime.datetime) -> None:
        """
        Adds an entry into our interactions DB with the corresponding message.
        :param message_id: int - message ID
        :param guild_id: int - guild ID
        :param user_id: int - user ID
        :param channel_id: int - channel ID
        :param message_type: str - message type
        :param message_content: str - message content
        :param timestamp: - datetime object
        :return: None
        """

        message = {
            "message_id": message_id,
            "guild_id": guild_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "message_type": message_type,
            "content": message_content,
            "timestamp": timestamp
        }

        self.insert(message)

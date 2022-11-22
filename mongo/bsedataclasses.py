"""
This is a file for Collection Classes in a MongoDB database.

A MongoDB database can have lots of Collections (basically tables). Each Collection should have a class here
that provides methods for interacting with that Collection.

This particular file contains Collection Classes for the 'bestsummereverpoints' DB.
"""

import datetime
import random
from typing import Optional, Union

from discordbot.bot_enums import AwardsTypes, StatTypes
from mongo import interface
from mongo.datatypes import Thread
from mongo.db_classes import BestSummerEverPointsDB


class AutoGeneratedBets(BestSummerEverPointsDB):
    """
    Class for interacting with the 'autogeneratedbets' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "autogeneratedbets")

    def insert_generated_bet(self, scenario_type: str, title: str, options: list):
        """
        Insert a bet into the DB that we can pull out later.

        :param scenario_type:
        :param title:
        :param options:
        :return:
        """

        document = {
            "type": scenario_type,
            "title": title,
            "options": options
        }

        self.insert(document)

    def get_bets_for_type(self, scenario_type: str) -> list:
        """
        Gets ALL bets for a specified type

        :param scenario_type:
        :return:
        """
        rets = self.query({"type": scenario_type})
        return rets

    def get_random_bets_for_type(self, scenario_type: str, amount: int = 3) -> list:
        """
        Gets a random sample of bets for a specified type

        :param scenario_type:
        :param amount:
        :return:
        """
        rets = self.get_bets_for_type(scenario_type)
        try:
            return random.sample(rets, int(amount))
        except ValueError:
            return rets


class SpoilerThreads(BestSummerEverPointsDB):
    """
    Class for interacting with the 'autogeneratedbets' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "spoilerthreads")

    def get_all_threads(self, guild_id: int) -> list[Thread]:
        """
        Gets all threads from the DB

        Args:
            guild_id (int): the guild to get the threads for

        Returns:
            list: list of Threads
        """
        return self.query({"guild_id": guild_id})

    def insert_spoiler_thread(
            self,
            guild_id: int,
            thread_id: int,
            name: str,
            created: datetime.datetime,
            owner: int,
            new_episode_day: Optional[int] = None
    ) -> list:
        """
        Insert a bet into the DB that we can pull out later.

        :return:
        """

        document = {
            "guild_id": guild_id,
            "thread_id": thread_id,
            "name": name,
            "day": new_episode_day,
            "active": True,
            "created": created,
            "owner": owner
        }

        return self.insert(document)

    def get_thread_by_id(self, guild_id: int, thread_id: int) -> Union[None, Thread]:
        """

        :param guild_id:
        :param thread_id:
        :return:
        """

        ret = self.query({"guild_id": guild_id, "thread_id": thread_id})
        if ret:
            return ret[0]
        return None


class TaxRate(BestSummerEverPointsDB):
    """
    Class for interacting with the 'taxrate' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "taxrate")
        self._cached_id = None

    def _set_default_doc(self) -> dict:
        """_summary_

        Returns:
            _type_: _description_
        """
        doc = {"type": "tax", "value": 0.1}
        self.insert(doc)
        return doc

    def get_tax_rate(self) -> float:

        if self._cached_id:
            ret = self.query({"_id": self._cached_id})
        else:
            ret = self.query({"type": "tax"})
            if not ret:
                ret = [self._set_default_doc(), ]

        if ret:
            self._cached_id = ret[0]["_id"]
            return ret[0]["value"]

    def set_tax_rate(self, tax_rate: float) -> None:

        if self._cached_id:
            update_doc = {"_id": self._cached_id}
        else:
            update_doc = {"type": "tax"}

        self.update(update_doc, {"$set": {"value": tax_rate}})


class CommitHash(BestSummerEverPointsDB):
    """
    Class for interacting with the 'taxrate' MongoDB collection in the 'bestsummereverpoints' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "hashes")

    def get_last_hash(self, guild_id: int) -> dict:
        ret = self.query({"type": "hash", "guild_id": guild_id})
        if ret:
            return ret[0]


class Awards(BestSummerEverPointsDB):
    def __init__(self):
        super().__init__()
        self._vault = interface.get_collection(self.database, "awards")

    def document_stat(
        self,
        guild_id: int,
        stat: StatTypes,
        month: str,
        value: Union[int, float, datetime.datetime, datetime.date],
        timestamp: datetime.datetime,
        short_name: str,
        annual: bool,
        **kwargs
    ) -> list:

        if type(value) == datetime.date:
            # convert date into something MongoDB wants to parse
            value = value.strftime("%Y-%m-%d")

        doc = {
            "type": "stat",
            "guild_id": guild_id,
            "stat": stat,
            "timestamp": timestamp,
            "month": month,
            "value": value,
            "short_name": short_name,
            "annual": annual
        }

        for key in kwargs:
            if key not in doc:
                doc[key] = kwargs[key]

        return self.insert(doc)

    def document_award(
        self,
        guild_id: int,
        user_id: int,
        award: AwardsTypes,
        month: str,
        eddies: int,
        value: Union[int, float],
        short_name: str,
        annual: bool,
        **kwargs
    ) -> list:
        """Insert an award into the DB

        Args:
            guild_id (int): server ID
            user_id (int): user ID
            award (AwardsTypes): the enum type of the award won
            month (str): a readable format like 'Oct 22'
            eddies (int): the eddies won
        """
        doc = {
            "type": "award",
            "guild_id": guild_id,
            "user_id": user_id,
            "award": award,
            "timestamp": datetime.datetime.now(),
            "month": month,
            "eddies": eddies,
            "value": value,
            "short_name": short_name,
            "annual": annual
        }

        for key in kwargs:
            if key not in doc:
                doc[key] = kwargs[key]

        return self.insert(doc)

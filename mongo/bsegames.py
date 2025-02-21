"""
This is a file for Collection Classes in a MongoDB database.

A MongoDB database can have lots of Collections (basically tables). Each Collection should have a class here
that provides methods for interacting with that Collection.

This particular file contains Collection Classes for the 'bestsummerevergameservers' DB.
"""

import datetime

from mongo import interface
from mongo.db_classes import BestSummerEverGameServersDB


class GameServers(BestSummerEverGameServersDB):
    """
    Class for interacting with the 'gameservers' MongoDB collection in the 'bestsummerevergameservers' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "gameservers")

    def insert_game_server(self, game_type: str, game: str, server_name: str, ip_address: str, port: int) -> None:
        """

        :param game:
        :param server_name:
        :param ip_address:
        :param port:
        :return:
        """
        doc = {
            "type": game_type,
            "game": game,
            "name": server_name,
            "ip": ip_address,
            "port": port,
            "rcon_port": port + 1
        }

        self.insert(doc)

    def get_all_game_servers(self) -> list:
        """

        :return:
        """
        return self.query({"display": True}, as_gen=False)


class GameServerInfo(BestSummerEverGameServersDB):
    """
    Class for interacting with the 'gameservers' MongoDB collection in the 'bestsummerevergameservers' DB
    """
    def __init__(self):
        """
        Constructor method that initialises the vault object
        """
        super().__init__()
        self._vault = interface.get_collection(self.database, "serverinfo")

    def update_player_count(self, amount):
        """

        :param amount:
        :return:
        """

        update_d = {"player_count": amount}
        if amount > 0:
            update_d["last_connection"] = datetime.datetime.now()

        ret = self.update(
            {"type": "player_count"},
            {"$set": update_d}
        )
        return ret

    def get_player_count(self):
        ret = self.query({"type": "player_count"}, as_gen=False)
        return ret[0]["player_count"]

    def get_debug_mode(self):
        ret = self.query({"type": "debug_mode"}, as_gen=False)
        return ret[0].get("debug_mode", False)

    def get_last_player_connected(self):
        ret = self.query({"type": "player_count"}, as_gen=False)
        return ret[0].get("last_connection")

from typing import List
from models.magic_castle import MagicCastle
import sqlite3


class User:
    def __init__(self, database_connection: sqlite3.Connection):
        self._database_connection = database_connection

    @property
    def full_name(self):
        raise NotImplementedError

    def get_all_magic_castles(self) -> List[MagicCastle]:
        raise NotImplementedError

    def create_empty_magic_castle(self) -> MagicCastle:
        raise NotImplementedError

    def get_magic_castle_by_hostname(self, hostname) -> MagicCastle:
        raise NotImplementedError


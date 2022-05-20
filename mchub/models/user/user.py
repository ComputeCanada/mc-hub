import sqlite3

from typing import List

from .. magic_castle.magic_castle import MagicCastle

class User:
    @property
    def full_name(self):
        return None

    @property
    def username(self):
        return None

    @property
    def public_keys(self):
        return []

    @property
    def projects(self):
        return []

    def get_all_magic_castles(self) -> List[MagicCastle]:
        raise NotImplementedError

    def create_empty_magic_castle(self) -> MagicCastle:
        raise NotImplementedError

    def get_magic_castle_by_hostname(self, hostname) -> MagicCastle:
        raise NotImplementedError

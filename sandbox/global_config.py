# Copyright (c) Minimasoft 2025

from pathlib import Path
from os import getenv


def _env(key: str, default=None):
    return getenv("BB_" + key, default)

_gconf_cache = None
def gconf(key: str):
    if _gconf_cache is None:
        _gconf_cache = {
            'DATA_PATH': Path(_env("DATA_PATH", "../data/")),
            'FILEDB_PATH': Path(_env("FILEDB_PATH", "../filedb")),
            'FILEDB_SALT': Path(_env("FILEDB_SALT", "bo_salt")),
        }
    return _gconf_cache[key]
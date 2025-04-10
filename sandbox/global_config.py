# Copyright (c) Minimasoft 2025

from pathlib import Path
from os import getenv


def _env(key: str, default=None):
    return getenv("BB_" + key, default)

_gconf_cache = None
def gconf(key: str):
    global _gconf_cache
    if _gconf_cache is None:
        from db_config import NormMeta, LLMTaskMeta
        _gconf_cache = {
            'DATA_PATH': Path(_env("DATA_PATH", "../data/")),
            'FILEDB_PATH': Path(_env("FILEDB_PATH", "../filedb")),
            'FILEDB_SALT': _env("FILEDB_SALT", "bo_salt"),
            'NORM_META': NormMeta(),
            'LLM_TASK_META': LLMTaskMeta(),
        }
    return _gconf_cache[key]

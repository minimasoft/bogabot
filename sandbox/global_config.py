# Copyright (c) Minimasoft 2025

from pathlib import Path
from os import getenv
from file_db import FileDBMeta


def _env(key: str, default=None):
    return getenv("BB_" + key, default)

_gconf_cache = None
def gconf(key: str):
    global _gconf_cache
    if _gconf_cache is None:
        _gconf_cache = {
            'DATA_PATH': Path(_env("DATA_PATH", "../data/")),
            'FILEDB_PATH': Path(_env("FILEDB_PATH", "../filedb")),
            'FILEDB_SALT': _env("FILEDB_SALT", "bo_salt"),
            'NORM_META': FileDBMeta('norm', 'ext_id'),
            'LLM_TASK_META': FileDBMeta('llm_task', 'task_key'),
        }
    return _gconf_cache[key]
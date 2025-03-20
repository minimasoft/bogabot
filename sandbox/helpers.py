# Copyright (c) Minimasoft 2025

from json import load
from gzip import open as gzopen


def load_json(fpath):
    with open(fpath, 'rt', encoding='utf-8') as jf:
        return load(jf)

def load_json_gz(fpath):
    with gzopen(fpath,'rt',encoding='utf-8') as jf:
        return load(jf)

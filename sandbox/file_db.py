#!/usr/bin/env python
# Copyright (c) 2025 Minimasoft

# write dict objects with types, never delete

import gzip
import json
import time
import random
import sys
from base58 import b58encode
from contextlib import contextmanager
from hashlib import sha256
from hmac import HMAC
from pathlib import Path
from time import sleep
from traceback import print_exc
from os import getpid


class FileDBMeta():
    def __init__(self, obj_type_s: str, obj_key_field_s: str):
        self.obj_type_s = obj_type_s
        self.obj_key_field_s = obj_key_field_s


class FileDBKeyEncoder():
    def __init__(self, salt_s: str, encoding: str='utf-8'):
        self.encoding = encoding
        self.key = salt_s.encode(encoding)

    def digest_s(self, target: str) -> str:
        return b58encode(
            HMAC(
                self.key,
                str(target).encode(self.encoding),
                sha256
                ).digest()
            ).decode(self.encoding)

class FileDB():
    def __init__(self, base_path: Path, salt_s: str, encoding='utf-8', tree_depth: int=3):
        self.tree_depth = tree_depth
        self.encoding = encoding
        self.key_enc = FileDBKeyEncoder(salt_s, encoding=encoding)
        self.base_path = base_path
        self._open = gzip.open

    def _obj_path(self, obj_type_s: str, b58key_s: str):
        path = self.base_path / obj_type_s
        for x in range(1, self.tree_depth+1):
            path = path / b58key_s[-x]
        path = path / b58key_s
        path.mkdir(parents=True, exist_ok=True)
        return path

    @contextmanager
    def _lock(self, obj_path: Path):
        lock_path = obj_path / ".lock"
        lock_success = False
        while lock_success == False:
            while lock_path.exists():
                sleep(0.001)  # async-io some day

            with open(lock_path, 'w') as lock_fp:
                lock_fp.write(str(getpid()))
                lock_fp.flush()
                lock_success = True
                yield lock_fp

            lock_path.unlink()


    def _read_part(self, part_path: Path) -> dict:
        with self._open(part_path, 'rt', encoding=self.encoding) as fp:
            return json.load(fp)


    def _write_part(self, part_path: Path, obj: dict):
        with self._open(part_path, 'wt', encoding=self.encoding) as fp:
            json.dump(obj, fp, ensure_ascii=False)


    def _new_part_name(self):
        return f"{time.time_ns()}.jgz"


    def _direct_read(self, obj_path: Path) -> dict:
        obj = dict()
        for data_part_path in sorted(obj_path.glob('*.jgz')):
            obj.update(self._read_part(data_part_path))
        return obj


    def read(self, key_s: str, meta: FileDBMeta) -> dict:
        b58key_s = self.key_enc.digest_s(key_s)
        obj_path = self._obj_path(meta.obj_type_s, b58key_s)
        return self._direct_read(obj_path)


    class NoOverwrite(Exception):
        pass

    def write(self, obj: dict, meta: FileDBMeta, overwrite: bool=True):
        if obj == {}:
            raise Exception("No empty objects")
        b58key_s = self.key_enc.digest_s(obj[meta.obj_key_field_s])
        obj_path = self._obj_path(meta.obj_type_s, b58key_s)
        with self._lock(obj_path):
            current_obj = self.read(obj[meta.obj_key_field_s], meta)
            new_data = {}
            for key in obj.keys():
                if key == meta.obj_key_field_s:
                    continue
                if key not in current_obj.keys():
                    new_data[key] = obj[key]
                else:
                    if type(obj[key]) != type(current_obj[key]) or obj[key] != current_obj[key]:
                        if overwrite == False:
                            raise FileDB.NoOverwrite
                        new_data[key] = obj[key]
            new_part_path = obj_path / self._new_part_name()
            self._write_part(new_part_path, new_data)

    def all_types(self):
        return [type_path.name for type_path in self.base_path.glob('*')]

    def all(self, obj_type_s: str):
        type_path = self.base_path / obj_type_s
        expr = "*"
        for x in range(1, self.tree_depth + 1):
            expr += "/*"
        for obj_path in type_path.glob(expr):
            yield self._direct_read(obj_path)


def __test__filedb__():
    test_path = Path("./__test")
    if(test_path.exists()):
        import shutil
        shutil.rmtree(test_path)

    db = FileDB(test_path, "db_salt")
    meta = FileDBMeta("test", "1")
    a = {"1": '1', "2": 2}
    b = {"1": '2', "2": 1}
    c = {"1": '1', "2": 4}
    db.write(a, meta)
    db.write(b, meta)
    db.write(c, meta)
    d = {"1": '2', "2": 4}
    try:
        db.write(d, meta, overwrite=False)
        print("overwrite test error")
    except FileDB.NoOverwrite as e:
        print("overwrite test pass")
    print(db.read('1',meta))
    print(db.read('2',meta))

def __explore__():
    db_path = Path(sys.argv[1])
    db_salt = str(sys.argv[2])
    db = FileDB(db_path, db_salt)
    if arg_n > 3:
        obj_type = sys.argv[3]
    else:
        for obj_type in db.all_types():
            print(obj_type)
        return

    if arg_n == 6:
        obj_key_f = sys.argv[4]
        obj_key_v = sys.argv[5]
        obj_meta = FileDBMeta(obj_type, obj_key_f)
        print(db.read(obj_key_v, obj_meta))
    else:
        for obj in db.all(obj_type):
            print(obj)


if __name__ == "__main__":
    arg_n = len(sys.argv)
    if arg_n == 1:
        __test__filedb__()
    else:
        __explore__()
        
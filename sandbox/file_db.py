#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft
# look mum no db

import gzip
import json
import time
import random
import shutil
import sys
from base58 import b58encode
from contextlib import contextmanager
from hashlib import sha256
from hmac import HMAC
from pathlib import Path
from time import sleep, time_ns, time
from traceback import print_exc
from os import getpid


class FileDBMeta():
    def __init__(self, obj_type_s: str, obj_key_field_s: str):
        self.obj_type_s = obj_type_s
        self.obj_key_field_s = obj_key_field_s
    
    def d(self) -> dict:
        return {
            'type': self.obj_type_s,
            'key': self.obj_key_field_s,
        }

class FileDBRecord(dict):
    def __init__(self, meta: FileDBMeta, *args, **kwargs):
        super(FileDBRecord,self).__init__(*args, **kwargs)
        self._extra = {}
        self._meta = meta

    def e(self) -> dict:
        return self._extra

    def m(self) -> FileDBMeta:
        return self._meta


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

    class Locked(Exception):
        pass

    @contextmanager
    def _lock(self, obj_path: Path, wait: bool=True):
        # TODO: this is not that good but it works most of the time
        lock_path = obj_path / ".lock"
        lock_success = False
        wait_n = 0
        while lock_success == False:
            while lock_path.exists():
                if wait == False:
                    raise FileDB.Locked
                wait_n = wait_n + 1
                sleep(0.001)  # async-io some day
                if wait_n > 1000:
                    print(f"locked in: {obj_path}")
                    wait_n = 0

            try:
                with open(lock_path, 'w') as lock_fp:
                    lock_fp.write(str(getpid()))
                    lock_fp.flush()
                    lock_success = True
                    yield lock_fp
            finally:
                lock_path.unlink()


    def _all_locks(self):
        expr = "*/*"
        for x in range(1, self.tree_depth + 1):
            expr += "/*"
        expr += "/.lock"
        for lock_path in self.base_path.glob(expr):
            yield lock_path

    def _read_part(self, part_path: Path) -> dict:
        with self._open(part_path, 'rt', encoding=self.encoding) as fp:
            return json.load(fp)


    def _write_part(self, part_path: Path, obj: dict):
        with self._open(part_path, 'wt', encoding=self.encoding) as fp:
            json.dump(obj, fp, ensure_ascii=False)

    def _new_part_name(self):
        return f"{time_ns()}.jgz"

    def _new_part_name_v2(self):
        return f"{time_ns()}.json.gz"

    def _direct_read(self, obj_path: Path, meta: FileDBMeta) -> FileDBRecord:
        obj = FileDBRecord(meta=meta)
        ctime = 0

        for data_part_path in sorted(obj_path.glob('*.json.gz')):
            p_ctime = data_part_path.stat().st_ctime
            if p_ctime > ctime:
                ctime = p_ctime
            record = self._read_part(data_part_path)
            if 'del' in record:
                for key in record['del']:
                    if key in obj:
                        obj.pop(key)
            if 'set' in record:
                obj.update(record['set'])
        obj.e()['time'] = ctime
        return obj


    def read(self, key_s: str, meta: FileDBMeta) -> FileDBRecord:
        b58key_s = self.key_enc.digest_s(key_s)
        obj_path = self._obj_path(meta.obj_type_s, b58key_s)
        obj = self._direct_read(obj_path, meta)
        return obj

    class NoOverwrite(Exception):
        pass

    def write(self, obj: FileDBRecord, overwrite: bool=True):
        meta = obj.m()
        if obj == {}:
            raise Exception("No empty objects")
        b58key_s = self.key_enc.digest_s(obj[meta.obj_key_field_s])
        obj_path = self._obj_path(meta.obj_type_s, b58key_s)
        with self._lock(obj_path) as l:
            current_obj = self.read(obj[meta.obj_key_field_s], meta)
            new_data = {}
            old_data = {}
            for key in obj.keys() - current_obj.keys():
                new_data[key] = obj[key]
            for key in obj.keys() & current_obj.keys():
                if type(obj[key]) != type(current_obj[key]) or obj[key] != current_obj[key]:
                    if overwrite == False:
                        raise FileDB.NoOverwrite
                    new_data[key] = obj[key]
                    old_data[key] = current_obj[key]
            del_keys = [ key for key in current_obj.keys() - obj.keys() ]
            record = { # TODO: maybe deprecate in favor of file ctime
                't': str(time_ns())
            }
            if len(del_keys) > 0:
                record['del'] = del_keys
            if new_data != {}:
                record['set'] = new_data
            # TODO: index processing, check fields for new_data, old_data, etc
            # TODO: hooks
            new_part_path = obj_path / self._new_part_name_v2()
            self._write_part(new_part_path, record)
            obj.e()['time'] = time()
    

    def delete(self, obj: FileDBRecord):
        meta = obj.m()
        b58key_s = self.key_enc.digest_s(obj[meta.obj_key_field_s])
        obj_path = self._obj_path(meta.obj_type_s, b58key_s)
        shutil.rmtree(obj_path)


    def all_types(self):
        return [type_path.name for type_path in self.base_path.glob('*')]


    def all(self, meta: FileDBMeta, since_s: float=0) -> FileDBRecord:
        type_path = self.base_path / meta.obj_type_s
        expr = "*"
        for x in range(1, self.tree_depth + 1):
            expr += "/*"
        for obj_path in type_path.glob(expr):
            if obj_path.stat().st_mtime >= since_s:
                data = self._direct_read(obj_path, meta)
                yield data


    def compress(self, meta: FileDBMeta, sure: bool=False):
        # TODO: make this safer by moving stuff
        assert sure == True
        type_path = self.base_path / meta.obj_type_s
        expr = "*"
        for x in range(1, self.tree_depth + 1):
            expr += "/*"
        for obj_path in type_path.glob(expr):
            data = self._direct_read(obj_path, meta)
            shutil.rmtree(obj_path)
            if data != {}:
                self.write(data)


def __test__filedb__():
    test_path = Path("./__test")
    if(test_path.exists()):
        shutil.rmtree(test_path)

    db = FileDB(test_path, "db_salt")
    meta = FileDBMeta("test", "1")
    a = FileDBRecord(meta, {"1": '1', "2": 2})
    b = FileDBRecord(meta, {"1": '2', "2": 1})
    c = FileDBRecord(meta, {"1": '1', "2": 4})
    db.write(a)
    db.write(b)
    db.write(c)
    d = FileDBRecord(meta, {"1": '2', "2": 4})
    try:
        db.write(d, overwrite=False)
        print("overwrite test error")
    except FileDB.NoOverwrite as e:
        print("overwrite test pass")
    print(db.read('1',meta))
    print(db.read('2',meta))
    b = FileDBRecord(meta, {"1": '2'})
    db.write(b)
    print(f"{db.read('2',meta)} == {b} ?")
    assert db.read('2',meta) == b


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
        print("[")
        for obj in db.all(obj_type):
            for key in obj.keys():
                if isinstance(obj[key], str):
                    if len(obj[key]) > 16:
                        obj[key] = obj[key][:16] 
            print(json.dumps(obj, indent=2, ensure_ascii=False))
            print(",")
        print("{}]")


if __name__ == "__main__":
    arg_n = len(sys.argv)
    if arg_n == 1:
        __test__filedb__()
    else:
        __explore__()
        
#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft

import json
import requests
import sys
import pycouchdb

from datetime import date
from datetime import datetime
from pathlib import Path
from file_db import FileDB, FileDBMeta
from global_config import gconf
from llm_tasks import FineTask
from time import time

from threading import Thread
from queue import Queue
import queue
import time
from os import getenv


class db_saver(Queue):

    def __init__(self, target_db, num_workers=16):
        Queue.__init__(self)
        server = pycouchdb.Server(getenv("COUCHDB_MAIN"))
        self.db = server.database(target_db)
        for i in range(num_workers):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()

    def add_record(self, data):
        self.put(data)

    def worker(self):
        while True:
            data = self.get()
            try:
                self.db.save(data, batch=True)
            except:
                pass
            self.task_done()


def main():

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )

    norm_meta = gconf("NORM_META")
    llm_task_meta = gconf("LLM_TASK_META")
    print(datetime.now().timestamp())
    last_time = 1747305260

    all_norms = file_db.all(norm_meta, since_s=last_time)

    norm_saver = db_saver('bogabot_v0_norm')
    for norm in all_norms:
        if 'ext_id' in norm:
            norm['_id'] = str(norm['ext_id'])
            norm_saver.add_record(norm)
    print("joining for norms")
    norm_saver.join()

   # task_db = server.database('bogabot_v0_llm_task')
    task_saver = db_saver('bogabot_v0_llm_task')
    for llm_task in file_db.all(llm_task_meta, since_s=last_time):
        llm_task['_id'] = str(llm_task['task_key'])
        task_saver.add_record(llm_task)
    print("joining for tasks")
    task_saver.join()
            


if __name__ == '__main__':
    main()


#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft

import json
import requests
import sys

from datetime import date
from pathlib import Path
from file_db import FileDB, FileDBMeta
from global_config import gconf
from llm_tasks import get_llm_task_map, NotEnoughData
from time import time


def main():
    last_id = 323758
    max_id = 321850

    llm_task_map = get_llm_task_map()

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )

    norm_meta = gconf("NORM_META")
    llm_task_meta = gconf("LLM_TASK_META")
    current_id = last_id 
    # Compress db, no need for historic changes now
    #print("compressing db")
    #start = time()
    #file_db.compress(norm_meta, sure=True)
    #file_db.compress(llm_task_meta, sure=True)
    #print(f"done in {time()-start:.3f}s")

    while current_id < max_id:
        print(current_id)
        norm = file_db.read(str(current_id), norm_meta)
        if norm != {}:
            norm_map = llm_task_map['norm']
            for attr in norm_map.keys():
                try:
                    if attr not in norm:
                        if norm_map[attr].check(norm):
                            llm_task = norm_map[attr].generate(norm)
                            llm_task_prev = file_db.read(llm_task[llm_task_meta.obj_key_field_s], llm_task_meta)
                            if llm_task_prev != {}:
                                print("nothing")
                            else:
                                file_db.write(llm_task)
                except NotEnoughData:
                    pass
        current_id = current_id + 1
    start = time()
    all_tasks = file_db.all(llm_task_meta)
    by_attr_count = {
        '_scanned': 0
    }
    for task in all_tasks:
        by_attr_count['_scanned'] += 1
        if 'start' not in task:
            norm_ext_id = int(task['target_key_v'])
            if norm_ext_id < 322000:
                # Clean-up old tasks
                file_db.delete(task)
            else:
                norm = file_db.read(str(task['target_key_v']), norm_meta)
                attr = task['target_attr']
                if attr in norm:
                    #print(f"WUT {llm_task} \n\n {norm}")
                    file_db.delete(task)
                if attr not in by_attr_count.keys():
                    by_attr_count[attr] = 1
                else:
                    by_attr_count[attr] += 1
    print(f"scan took: {(time()-start):.2f}")
    print(by_attr_count)


if __name__ == '__main__':
    main()


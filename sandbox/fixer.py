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


def main():
    last_id = 3419000
    max_id = 322950

    llm_task_map = get_llm_task_map()

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    norm_meta = gconf("NORM_META")
    llm_task_meta = gconf("LLM_TASK_META")
    current_id = last_id 
    while current_id < max_id:
        print(current_id)
        norm = file_db.read(str(current_id), norm_meta)
        if norm != {}:
            dirty = False
            if 'law_ref' in norm:
                if len(norm['law_ref']) > 0:
                    if isinstance(norm['law_ref'][0], str):
                        norm.pop('law_ref')
                        dirty = True
            if dirty:
                file_db.write(norm, norm_meta)
            norm_map = llm_task_map['norm']
            for attr in norm_map.keys():
                try:
                    if attr not in norm:
                        if norm_map[attr].check(norm, norm_meta.d()):
                            llm_task = norm_map[attr].generate(norm, norm_meta.d())
                            llm_task_prev = file_db.read(llm_task[llm_task_meta.obj_key_field_s], llm_task_meta)
                            if llm_task_prev != {}:
                                print("nothing")
                            else:
                                file_db.write(llm_task, llm_task_meta)
                except NotEnoughData:
                    pass
        current_id = current_id + 1
    all_tasks = file_db.all(llm_task_meta.obj_type_s)
    by_attr_count = {}
    for task in all_tasks:
        if 'start' not in task:
            norm = file_db.read(str(task['target_key_v']), norm_meta)
            attr = task['target_attr']
            if attr in norm.keys():
                print(f"WUT {llm_task} \n\n {norm}")
            if attr not in by_attr_count.keys():
                by_attr_count[attr] = 1
            else:
                by_attr_count[attr] += 1

    print(by_attr_count)
        


if __name__ == '__main__':
    main()


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
    last_id = 322000
    max_id = 322950

    llm_task_map = get_llm_task_map()

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    norm_meta = gconf("NORM_META")
    llm_task_meta = gconf("LLM_TASK_META")
    all_for_date = file_db.all(llm_task_meta)
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
                            # TODO: check previous task diff?
                            file_db.write(llm_task, llm_task_meta)
                except NotEnoughData:
                    pass
        current_id = current_id + 1
        


if __name__ == '__main__':
    main()


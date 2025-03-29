#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft

import json
import requests
import sys
from csv import DictWriter

from datetime import date
from time import asctime
from pathlib import Path
from file_db import FileDB, FileDBMeta
from global_config import gconf
from llm_tasks import get_llm_task_map, NotEnoughData


def main():
    last_id = 321900
    max_id = 324000

    llm_task_map = get_llm_task_map()

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    norm_meta = gconf("NORM_META")
    attrs = list("name,gov_id,gov_section,position,position_start,position_duration_days".split(","))
    with open('test.csv','w',encoding='utf-8') as csv_f:
        csv_f.write(f"# bogabot data: appoint_list dump {asctime()}\n")
        csv_f.write(f"# errata:\n")
        csv_f.write(f"# - Algunos casos de designación de interventor en organizaciones son clasificados por error\n")
        csv_f.write(f"# - gov_id puede ser dni o cuit\n")
        writer = DictWriter(csv_f, fieldnames=attrs, dialect='excel')
        writer.writeheader()
        for norm in file_db.all(norm_meta.obj_type_s):
            if 'appoint_list' in norm and len(norm['appoint_list']) > 0:
                writer.writerows(norm['appoint_list'])


if __name__ == '__main__':
    main()


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
    attrs = list("norm_publish_date,name,gov_id,gov_section,position,position_start,position_duration_days,norm_official_id,norm_link".split(","))
    with open('test.csv','w',encoding='utf-8') as csv_f:
        writer = DictWriter(csv_f, fieldnames=attrs, dialect='excel')
        writer.writeheader()
        for norm in sorted(filter(lambda x: 'ext_id' in x,file_db.all(norm_meta)),key=lambda n: int(n['ext_id'])):
            if 'appoint_list' in norm and len(norm['appoint_list']) > 0:
                for appoint in norm['appoint_list']:
                    appoint['norm_official_id'] = norm['official_id']
                    if len(appoint['norm_official_id']) <= 1:
                        continue
                    appoint['norm_link'] = f'=HYPERLINK("{norm["data_link"]}")'
                    appoint['norm_publish_date'] = norm['publish_date']
                    writer.writerow(appoint)


if __name__ == '__main__':
    main()


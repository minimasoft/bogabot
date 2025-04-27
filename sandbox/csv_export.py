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
    last_id = 300700
    max_id = 324000

    llm_task_map = get_llm_task_map()

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    norm_meta = gconf("NORM_META")
    attrs = list("norm_publish_date,name,gov_id,gov_section,position,position_start,position_duration_days,norm_official_id,norm_link".split(","))
    attrs_r = list("norm_publish_date,name,gov_id,gov_section,position,position_end,norm_official_id,norm_link".split(","))
    with open('appoint.csv','w',encoding='utf-8') as csv_f:
        with open('resign.csv','w', encoding='utf-8') as csv_r:
            writer = DictWriter(csv_f, fieldnames=attrs, dialect='excel')
            writer_r = DictWriter(csv_r, fieldnames=attrs_r, dialect='excel')
            writer.writeheader()
            writer_r.writeheader()
            for norm in sorted(filter(lambda x: 'ext_id' in x,file_db.all(norm_meta)),key=lambda n: int(n['ext_id'])):
                if 'appoint_list' in norm and len(norm['appoint_list']) > 0:
                    for appoint in norm['appoint_list']:
                        appoint['norm_official_id'] = norm['official_id']
                        if len(appoint['norm_official_id']) <= 1:
                            continue
                        appoint['norm_link'] = f'=HYPERLINK("{norm["data_link"]}")'
                        appoint['norm_publish_date'] = norm['publish_date']
                        if 'gov_id' in appoint:
                            appoint['gov_id'] = str(appoint['gov_id']).replace('.','')
                        try:
                            writer.writerow(appoint)
                        except ValueError as ve:
                            print(appoint)
                            print(ve)
                if 'resign_list' in norm and len(norm['resign_list']) > 0:
                    for resign in norm['resign_list']:
                        resign['norm_official_id'] = norm['official_id']
                        if len(resign['norm_official_id']) <= 1:
                            continue
                        resign['norm_link'] = f'=HYPERLINK("{norm["data_link"]}")'
                        resign['norm_publish_date'] = norm['publish_date']
                        if 'gov_id' in resign:
                            resign['gov_id'] = str(resign['gov_id']).replace('.','')
                        try:
                            writer_r.writerow(resign)
                        except ValueError as ve:
                            print(resign)
                            print(ve)


if __name__ == '__main__':
    main()


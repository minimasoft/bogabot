#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft

import json
import requests
import sys

from datetime import date
from pathlib import Path
from file_db import FileDB, FileDBMeta
from global_config import gconf
from llm_tasks import FineTask
from time import time


def main():

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )

    norm_meta = gconf("NORM_META")

    all_norms = file_db.all(norm_meta)
    total_2025_vialidad = 0
    total_2025_multas = 0
    total_2025_rio_uruguay = 0
    total_process = 0
    fines = []
    for norm in all_norms:
        if 'subject' not in norm:
            pass
        elif 'vialidad' in norm['subject'].lower():
            total_2025_vialidad += 1
            if '#multa' in norm['tags']:
                if 'fine_list' in norm:
                    for fine in norm['fine_list']:
                        fine['date'] = norm['publish_date']
                        fine['link'] = norm['data_link']
                        fines.append(fine)
                    total_process += 1

                total_2025_multas += 1
                if 'CAMINOS DEL RÍO URUGUAY' in norm['full_text'].upper():
                    total_2025_rio_uruguay += 1
    print('#'*80)
    print(f"Informe preliminar multas Vialidad gobierno Javier Milei")
    print('-'*80)
    print(f"Resoluciones de vialidad: {total_2025_vialidad}")
    print(f"De las cuales clasifican como multas: {total_2025_multas}")
    print(f"De las cuales se menciona a CAMINOS DEL RÍO URUGUAY: {total_2025_rio_uruguay}")
    print('#'*80)
    total_up = sum([fine['amount_up'] for fine in fines])
    print(f"Total de las multas procesadas({total_process}) en U.P.: {total_up}")
    print('#'*80)
    print("CSV:")
    print("date,target,amount_up,reason_brief,authority,link")
    for f in fines:
        print(f"{f['date']},{f['target']},{int(f['amount_up'])},'{f['reason_brief']}','{f['authority']}',HYPERLINK({f['link']})")

if __name__ == '__main__':
    main()


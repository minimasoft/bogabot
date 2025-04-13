#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft

import json
import requests
import sys

from datetime import date
from pathlib import Path
from file_db import FileDB, FileDBMeta
from global_config import gconf
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
    for norm in all_norms:
        if 'subject' not in norm:
            pass
        elif 'vialidad' in norm['subject'].lower():
            total_2025_vialidad += 1
            if '#multa' in norm['tags']:
                total_2025_multas += 1
                if 'CAMINOS DEL RÍO URUGUAY' in norm['full_text'].upper():
                    total_2025_rio_uruguay += 1
    print('#'*80)
    print(f"Informe preliminar 2025")
    print('-'*80)
    print(f"Resoluciones de vialidad: {total_2025_vialidad}")
    print(f"De las cuales clasifican como multas: {total_2025_multas}")
    print(f"De las cuales se menciona a CAMINOS DEL RÍO URUGUAY: {total_2025_rio_uruguay}")
    print('#'*80)

if __name__ == '__main__':
    main()


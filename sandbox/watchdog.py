#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025
# wof wof

import sys
import os
from pathlib import Path
from time import time_ns, sleep, ctime
from global_config import gconf
from file_db import FileDB, FileDBMeta


def check_dead_tasks(db, task_meta: dict, timeout_s: float=360.0):
    total = 0
    for task in db.all(task_meta.d()['type']):
        if 'start' in task and 'end' not in 'task':
            start = int(task['start'])
            elapsed_s = (time_ns() - int(task['start']))/10.0**9
            if elapsed_s > timeout_s:
                total = total + 1
                print(
                    f"'{task['target_type']}[{task['target_key_v']}].{task['target_attr']}'" +\
                        f" task dead for {elapsed_s/60:.2f} minutes will retry.")
                task.pop('start')
                db.write(task, task_meta)
    print(f"Found {total} unresponsive {task_meta.d()['type']}.")

def check_locks(db):
    for lock_path in db._all_locks():
        print(lock_path)
        print(lock_path.stat())
        # TODO: what to do? 

def main(argv: list) -> int:
    db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    llm_task_meta = gconf("LLM_TASK_META")
    norm_meta = gconf("NORM_META")
    running = True
    while running:
        print(f"[{ctime()}]: Watching from pid:{os.getpid()}...")
        check_dead_tasks(db, llm_task_meta)
        check_locks(db)
        sleep(3.14)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
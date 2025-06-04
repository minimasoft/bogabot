#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025
# wof wof

import sys
import os
from pathlib import Path
from time import time_ns, sleep, ctime, time
from global_config import gconf
from file_db import FileDB, FileDBMeta


def check_dead_tasks(db, task_meta: FileDBMeta, since_s: float=0.0, timeout_s: float=50.0):
    unresponsive = 0
    processing = 0
    newest_task_s = since_s - timeout_s
    start_s = time()
    all_tasks = db.all(task_meta, newest_task_s)
    for task in all_tasks:
        if task.e()['time'] > newest_task_s:
            newest_task_s = task.e()['time']

        if 'start' in task and 'end' not in task:
            start = int(task['start'])
            elapsed_s = (time_ns() - int(task['start']))/10.0**9
            timeout_fix_s = timeout_s
            if task['target_attr'] == 'analysis':
                timeout_fix_s += 900 # Analysis are really slow now :(
            if elapsed_s > timeout_fix_s:
                unresponsive = unresponsive + 1
                print(
                    f"'{task['target_type']}[{task['target_key_v']}].{task['target_attr']}'" +\
                        f" task dead for {elapsed_s/60:.2f} minutes will retry.")
                task.pop('start')
                db.write(task)
            else:
                processing = processing + 1

    print(f"Found {unresponsive} unresponsive and {processing} processing {task_meta.d()['type']} in {(time()-start_s):.3f}s.")
    return newest_task_s

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
    llm_task_check_time_s = 0
    while running:
        print(f"[{ctime()}]: Watching from pid:{os.getpid()}...")
        llm_task_check_time_s = check_dead_tasks(db, llm_task_meta, since_s=llm_task_check_time_s)
        #check_locks(db)
        sleep(6.28)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

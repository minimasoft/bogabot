#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025

import base64
import json
import os
import sys

from pathlib import Path
from time import time_ns, sleep
from file_db import FileDB, FileDBMeta
from global_config import gconf
from llm_tasks import get_llm_task_map, NotEnoughData, BadLLMData

from openai import OpenAI

def load_json(fpath):
    with open(fpath, 'rt', encoding='utf-8') as jf:
        return json.load(jf)

worker_config_path = Path(sys.argv[1]) # i.e. 'worker_local.json'
worker_config = load_json(worker_config_path)
#api_key = str
#num_ctx = int
#rpm = int
#rpd = int

MODEL="qwen-qwq-32b"


def query_deep(model_name:str, prompt:str) -> str:
    global worker_config
    client = OpenAI(
        api_key=worker_config['api_key'],
        base_url="https://api.groq.com/openai/v1/"
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are bogabot, a helpful and precise law asistant for Argentina"},
            {"role": "user", "content": prompt}
        ],
        stream=False
    )
    llm_response = response.choices[0].message.content
    is_thinking = llm_response.find("<think>")
    end_of_think = llm_response.find("</think>")
    if end_of_think > 0:
        llm_response = llm_response[(end_of_think+8):]
    if is_thinking >= 0 and end_of_think < 0:
        print("--------------------------------------------------")
        print("---------THINK OUTPUT ERROR-----:O :O :O----------")
        print("--------------------------------------------------")
        print(f"Input:\n{prompt}\n")
        print("--------------------------------------------------")
        print("------------------------------------------OMG-----")
        print("--------------------------------------------------")
        
    return llm_response

# TODO: universal hooks for file db
def _hook_update_norm(norm: dict, norm_meta_d:dict, norm_map: dict):
    for attr in norm_map.keys():
        try:
            if attr not in norm.keys():
                if norm_map[attr].check(norm, norm_meta_d):
                    llm_task = norm_map[attr].generate(norm, norm_meta_d)
                    yield llm_task
        except NotEnoughData:
            pass


def __main__():
    global worker_config
    print(f"Bogabot groq api worker pid={os.getpid()}")
    db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    llm_task_meta = gconf("LLM_TASK_META")
    task_type = llm_task_meta.obj_type_s
    norm_meta = gconf("NORM_META")
    attr_arg = sys.argv[2]
    task_map = get_llm_task_map()
    if attr_arg.find(',') > 0:
        attr_list = [
            attr.strip()
            for attr in attr_arg.split(',')
            ]
    else:
        attr_list = [ attr_arg ]

    last_start = 0
    # 60 seconds / requests_per_minute in ns + 1 second
    nspr = (60*10**9) / int(worker_config['rpm']) + 10**9
    running = True
    while running:
        for target_attr in attr_list:
            for llm_task in filter(lambda t: target_attr == t['target_attr'], db.all(task_type)):
                if 'start' in llm_task:
                    continue
                if len(llm_task['prompt']) > int(worker_config['num_ctx'])*3.5:
                    print(f"Context too big for this worker: {len(llm_task['prompt'])}")
                    continue
                # rate limit
                while time_ns() < (last_start+nspr):
                    sleep(0.1)

                last_start = time_ns()
                llm_task['start'] = str(last_start)
                try:
                    db.write(llm_task, llm_task_meta, overwrite=False)
                except FileDB.NoOverwrite:
                    continue
                llm_output = query_deep(MODEL, llm_task['prompt'])
                print(llm_output)
                llm_task['model'] = MODEL
                llm_task['num_ctx'] = worker_config['num_ctx']
                llm_task['end'] = str(time_ns())
                target_obj = db.read(llm_task['target_key_v'], norm_meta)
                assert target_obj != {}
                try:
                    task_map[
                        llm_task['target_type']][
                            llm_task['target_attr']
                            ].post_process(llm_output, target_obj)
                except BadLLMData:
                    print("BADLLMDATA")
                    # TODO: maybe tip next run to change the seed?
                    continue 
                db.write(target_obj, norm_meta)
                # only write llm_task with 'end' after storing the result
                db.write(llm_task, llm_task_meta)
                for new_task in _hook_update_norm(target_obj, norm_meta.d(), task_map['norm']):
                    db.write(new_task, llm_task_meta)
        print("Task cycle done. Will re-scan in 1 second...")
        sleep(0.99)


if __name__ == '__main__':
    __main__()
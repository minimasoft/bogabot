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
import concurrent.futures
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
wait_cycle_s = 5.0

def query_deep(prompt:str) -> str:
    global worker_config
    if len(prompt) > int(worker_config['num_ctx'])*3.5:
        print(f"Context too big for this worker({worker_config['model']}): {len(prompt)}")
        raise Exception
    client = OpenAI(
        api_key=worker_config['api_key'],
        base_url=worker_config['base_url']
    )

    response = client.chat.completions.create(
        model=worker_config['model'],
#        service_tier="flex",
        messages=[
            {"role": "system", "content": "You are a helpful law research asistant for Argentina. Make sure to write answers in spanish only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.42, # TODO: make this a conf param
        stream=False
    )
    llm_response = response.choices[0].message.content
    response_parts = llm_response.split("</think>")
    if len(response_parts) > 1:
        llm_response = response_parts[-1]
        if len(response_parts) > 2:
            print(f"{'*'*80}\nWeird 3 part response: {response_parts}\n{'*'*80}") 
    return llm_response

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
    task_map = get_llm_task_map()
    attr_list = worker_config['tasks']

    last_start = 0
    # 60 seconds / requests_per_minute in ns + 1 second
    nspr = (60*10**9) / int(worker_config['rpm']) + 10**9
    running = True
    last_check_s = 1748960000
    while running:
        all_tasks = sorted(filter(lambda t: int(t['target_key_v']) > 326410 and 'start' not in t and t['target_attr'] in attr_list, db.all(llm_task_meta, last_check_s)), key=lambda t: int(t['target_key_v']), reverse=False)
        for target_attr in attr_list:
            for llm_task in filter(lambda t: target_attr == t['target_attr'], all_tasks):
                print(f"Checking task for {llm_task['target_key_v']}")
                if llm_task.e()['time'] > last_check_s:
                    last_check_s = llm_task.e()['time']
                target_obj = db.read(llm_task['target_key_v'], norm_meta)
                assert target_obj != {}

                if llm_task['target_attr'] in target_obj:
                    print("duplicated task? TODO: implement force")
                    continue

                while time_ns() < (last_start+nspr):
                    print('.')
                    sleep(0.33)
                llm_task['start'] = time_ns()
                try:
                    db.write(llm_task, overwrite=False)
                except FileDB.NoOverwrite:
                    continue
                last_start = time_ns()

                prompt = llm_task['prompt']
                results = {}
                if type(prompt) != str:
                    print('='*80)
                    print("processing map reduce analysis")
                    print('-'*80)
                    reducer = prompt.pop('reducer')
                    reduce_context = ""
                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                        results = []
                        for k in prompt.keys():
                            n = len(prompt[k])
                            if n > 419999:
                                print("TODO: exta-big law... Can't crunch now. GRRRR")
                                print(k)
                                continue

                            def get_context_chunk(prompt):
                                result = ""
                                retries = 3
                                while result == "" and retries > 0:
                                    try:
                                        result = query_deep(prompt)
                                    except Exception:
                                        retries -=1
                                return result

                            results.append(executor.submit(get_context_chunk, prompt[k]))
                            print(f"queued {n} context for {k}")

                        for future in concurrent.futures.as_completed(results):
                            reduce_context += future.result()
                            reduce_context += "\n\n"
                    reducer = reducer.replace('_reducer_', reduce_context)
                    print(reducer)
                    print('='*80)
                    llm_output = ""
                    retry=5
                    while llm_output == "" and retry >= 0:
                        try:
                            llm_output = query_deep(reducer)
                        except Exception as e:
                            print(e)
                            print("WILL RETRY!!!")
                            sleep(1)
                            retry -=1

                else:
                    try:
                        llm_output = query_deep(prompt)
                    except Exception as e:
                        print(e)
                        continue


                llm_task['end'] = str(time_ns())
                llm_task['model'] = worker_config['model']
                llm_task['num_ctx'] = worker_config['num_ctx']

                print(f"llm_output from {worker_config['model']}:\n{llm_output}")

                try:
                    task_map[
                        llm_task['target_type']][
                            llm_task['target_attr']
                            ].post_process(llm_output, target_obj)
                except BadLLMData:
                    print("BADLLMDATA")
                    # TODO: maybe tip next run to change the seed?
                    continue 

                db.write(target_obj)
                # only write llm_task with 'end' after storing the result
                db.write(llm_task)
                # rate_limit if needed
                sleep(1)

        print(f"Task cycle done. Will re-scan in {wait_cycle_s:.2f} seconds...")
        sleep(wait_cycle_s)


if __name__ == '__main__':
    __main__()

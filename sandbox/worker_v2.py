#!/usr/bin/env python
# Copyright Minimasoft (c) 2025
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter, Retry
import markdown
import sys
import os
import json
from time import time_ns, sleep
from file_db import FileDB, FileDBMeta
from global_config import gconf
from llm_tasks import get_llm_task_map, NotEnoughData


def load_json(fpath):
    with open(fpath, 'rt', encoding='utf-8') as jf:
        return json.load(jf)

worker_config_path = Path(sys.argv[1]) # i.e. 'worker_local.json'
worker_config = load_json(worker_config_path)

ollama_url = worker_config['ollama_base_url']
ollama_token = worker_config['ollama_login_token']
ollama_test = f"{ollama_url}/{ollama_token}"

ollama_session = requests.Session()
ollama_session.get(ollama_test, verify=False)


MODEL="qwq:32b"
#MODEL="huihui_ai/qwen2.5-1m-abliterated:14b"

# Move this to generic LLM-API call with streaming support
def query_ollama(model_name, prompt):
    global worker_config
    try:
        # Construct the Ollama API URL
        base_url = f"{ollama_url}/api/generate"

        # Prepare the payload for the request
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                # Bogabot personality 1.0
                "temperature": 0.42,
                "seed": 42, # guaranteed to be random
                "top_k": 24,
                "top_p": 0.5,
                "num_ctx": worker_config['ollama_num_ctx'],
            }
            "system": "Tu nombre es Bogabot. Eres un asistente legal preciso que genera reportes a pedido."
        }

        # Make the POST request to Ollama API
        response = ollama_session.post(base_url, json=payload, verify=False)
        response.raise_for_status()

        # Extract and return the generated text from the response
        data = response.json()
        print(f"""stats:
 - prompt_eval_count: {data['prompt_eval_count']}
 - eval_count:  {data['eval_count']}
 - gpu_time: {data['total_duration']/1000000}""")

        llm_response = data["response"]
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

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with Ollama API: {e}")
        return None


# TODO: universal hooks for file db
def _hook_update_norm(norm: dict, norm_meta_d:dict, norm_map: dict):
    for attr in norm_map.keys():
        try:
            if norm_map[attr].check(norm, norm_meta_d):
                llm_task = norm_map[attr].generate(norm, norm_meta_d)
                yield llm_task
        except NotEnoughData:
            pass


def __main__():
    global worker_config
    print(f"Bogabot worker pid={os.getpid()} ollama_url={ollama_url}")
    db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    llm_task_meta = gconf("LLM_TASK_META")
    norm_meta = gconf("NORM_META")
    target_attr = sys.argv[2]
    task_map = get_llm_task_map()

    running = True
    while running:
        for llm_task in db.all(llm_task_meta.obj_type_s):
            if target_attr != llm_task['target_attr']:
                continue
            if 'start' in llm_task:
                continue
            llm_task['start'] = str(time_ns())
            llm_task['model'] = MODEL
            llm_task['num_ctx'] = worker_config['ollama_num_ctx']
            try:
                db.write(llm_task, llm_task_meta, overwrite=False)
            except FileDB.NoOverwrite:
                continue
            llm_output = query_ollama(MODEL, llm_task['prompt'])
            llm_task['end'] = str(time_ns())
            db.write(llm_task, llm_task_meta)
            target_obj = db.read(llm_task['target_key_v'], norm_meta)
            print(task_map[llm_task['target_type']][llm_task['target_attr']].post_process(llm_output, target_obj))
            db.write(target_obj, norm_meta)
            for new_task in _hook_update_norm(target_obj, norm_meta.d(), task_map['norm']):
                db.write(new_task, llm_task_meta)
        print("Task cycle done... Will re-scan in 1 second")
        sleep(0.99)


if __name__ == '__main__':
    __main__()

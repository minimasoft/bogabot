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

from google import genai
from google.genai import types


def load_json(fpath):
    with open(fpath, 'rt', encoding='utf-8') as jf:
        return json.load(jf)

worker_config_path = Path(sys.argv[1]) # i.e. 'worker_local.json'
worker_config = load_json(worker_config_path)

gemini_api_key = worker_config['api_key']

MODEL="gemini-2.0-flash-thinking-exp-01-21"


def query_gemini(model_name:str, prompt:str) -> str:
    global worker_config
    client = genai.Client(
        api_key=worker_config['api_key'],
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    #TODO: tune personality for bogabot
    generate_content_config = types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.95,
        top_k=64,
        max_output_tokens=65536,
        response_mime_type="text/plain",
    )

    full_response = ""
    for chunk in client.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    ):
        full_response += chunk

    return full_response

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
    print(f"Bogabot gemini worker pid={os.getpid()}")
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

    running = True
    while running:
        for target_attr in attr_list:
            for llm_task in filter(lambda t: target_attr == t['target_attr'], db.all(task_type)):
                if 'start' in llm_task:
                    continue
                if len(llm_task['prompt']) > (worker_config['ollama_num_ctx'] * 3.5):
                    print(f"Context too big for this worker: {len(llm_task['prompt'])}")
                    continue

                llm_task['start'] = str(time_ns())
                try:
                    db.write(llm_task, llm_task_meta, overwrite=False)
                except FileDB.NoOverwrite:
                    continue
                llm_output = query_ollama(MODEL, llm_task['prompt'])
                llm_task['model'] = MODEL
                llm_task['num_ctx'] = worker_config['ollama_num_ctx']
                llm_task['end'] = str(time_ns())
                target_obj = db.read(llm_task['target_key_v'], norm_meta)
                assert target_obj != {}
                try:
                    task_map[
                        llm_task['target_type']][
                            llm_task['target_attr']
                            ].post_process(llm_output, target_obj)
                except BadLLMData:
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
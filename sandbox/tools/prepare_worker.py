#!/home/user/src/bogabot/venv/bin/python
# Copyright (c) 2025 Minimasoft

from pathlib import Path
import sys
import json
import requests

with open(sys.argv[1],'rt') as f:
    config = json.load(f)

TARGET_MODEL='qwq:32b'

ollama_url = config['ollama_base_url']
ollama_token = config['ollama_login_token']
ollama_test = f"{ollama_url}/{ollama_token}"

ollama_session = requests.Session()
ollama_session.get(ollama_test, verify=False)

#list models

api_res = ollama_session.get(f"{ollama_url}/api/tags", verify=False)

api_res.raise_for_status()
models = api_res.json()["models"]

try:
    model = next(model for model in models if model["name"] == TARGET_MODEL)
    print(f"model ready: {model}")
except StopIteration:
    print(f"model {TARGET_MODEL}  not found... pulling")
    api_res = ollama_session.post(
        f"{ollama_url}/api/pull",
        json={"model": TARGET_MODEL, "stream": False},
        verify=False)
    api_res.raise_for_status()
    print(api_res.json())


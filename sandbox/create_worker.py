#!/usr/bin/env python
import sys
import json

full_url = sys.argv[1]
base_url = full_url[:full_url.find('/?token')]
token_part = full_url[len(base_url):]
worker = {
    "ollama_base_url": base_url,
    "ollama_login_token": token_part,
    "ollama_num_ctx": 130031,
}
print(json.dumps(worker,indent=2))

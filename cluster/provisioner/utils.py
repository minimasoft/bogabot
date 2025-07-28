# Copyright Minimasoft (c) 2025

# HTTP

from requests.adapters import HTTPAdapter, Retry
from requests import Session, Response

def http_session() -> Session:
    session = Session()
    retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        })
    return session

def http_get(url, session=None, **kwargs) -> Response:
    session = session or http_session()
    return session.get(url, timeout=(3, 30), **kwargs)

def http_post(url, session=None, **kwargs) -> Response:
    session = session or http_session()
    return session.post(url, timeout=(3, 30), **kwargs)

def http_put(url, session=None, **kwargs) -> Response:
    session = session or http_session()
    return session.put(url, timeout=(3, 30), **kwargs)

def http_delete(url, session=None, **kwargs) -> Response:
    session = session or http_session()
    return session.put(url, timeout=(3, 30), **kwargs)

def step(msg, fun, retry_max=9):
    callable = fun
    print(f"-> {msg}")
    success = False
    retry = 0
    while success is False:
        try:
            result = callable()
            success = True
        except Exception as e:
            print("!Unexpected exception!")
            print(e)
            retry += 1
            if retry > retry_max:
                raise e
            print("retrying...")
    return result

    
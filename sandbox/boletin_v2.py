#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025
# New BO scrapper that can see the future (tm)

import json
import requests
import sys
import signal

from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path
from requests.adapters import HTTPAdapter, Retry
from file_db import FileDB, FileDBMeta, FileDBRecord
from global_config import gconf
from time import sleep


def bo_gob_ar_url():
    return "https://www.boletinoficial.gob.ar"

def bo_gob_ar_session():
    session = requests.Session()
    retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        })
    session.get(f"{bo_gob_ar_url()}/")
    return session


def scan_bo_gob_ar_section_one(current_id, meta, peek=False):
    session = bo_gob_ar_session()
    data_link =f"{bo_gob_ar_url()}/detalleAviso/primera/{current_id}/1" # Yes... I know. Did you know?

    print(f"scanning: {data_link}")

    with session.get(data_link) as response:
        soup = BeautifulSoup(response.text, 'html.parser')

        title_div = soup.find('div', {'id': 'tituloDetalleAviso'})
        if title_div is None:
            return False if peek else None
        if peek:
            return True

        norm = FileDBRecord(meta)

        norm['subject'] = title_div.find('h1').text.strip()

        if title_div.find('h2'):
            norm['name'] = title_div.find('h2').text.strip()
        else:
            norm['name'] = ""

        if title_div.find('h6'):
            more_data = title_div.find('h6').text.strip()
            norm['official_id'] = more_data
        else:
            norm['official_id'] = ""
        
        fecha = None

        for p_el in soup.find_all('p',{'class':'text-muted'}):
            if p_el.text.find('Fecha de publi') >= 0:
                date_text = p_el.text.split('n ')[1].strip()
                if date_text.find('/') > 0:
                    date_el = date_text.split('/')
                elif date_text.find('-') > 0:
                    date_el = date_text.split('-')
                else:
                    break
                fecha = date(int(date_el[2]), int(date_el[1]), int(date_el[0]))
                break
        
        if fecha is None:
            raise Exception("T.T")

        for script in soup(['script', 'meta', 'link', 'style']):
            script.decompose()  # Removes the tag completely from the tree

        body = str(soup.find('div', {'id': 'cuerpoDetalleAviso'}).contents[1])

        norm['full_text'] = body

        # TODO: full text se transforma en parseable reemplazando </p> y <p>
        # TODO: anexos?

        norm['publish_date'] = f"{fecha.year}-{fecha.month:02}-{fecha.day:02}"
        norm['data_link'] = data_link
        norm['ext_id'] = current_id

    return norm


class StateMachine():
    # TODO: contracts
    def __init__(self):
        pass

    def run(self) -> dict:
        pass


class ScanMachine(StateMachine):
    DEFAULT_START = 325645
    STEP = 13
    MAX_DISTANCE = 500

    def __init__(self, state: dict, norm_db_load, norm_online_peek):
        # def norm_db_load(int_id) -> dict, empty dict for None
        # def norm_online_peek(int_id) -> bool
        StateMachine.__init__(self)
        self._user_start_id = state['last_id'] if 'last_id' in state else ScanMachine.DEFAULT_START
        self._current_id = self._user_start_id
        while norm_db_load(self._current_id) != {}:
            self._current_id += 1
        self._scan_start_id = self._current_id
        self._norm_online_peek = norm_online_peek
        print(f"scanner will start at {self._scan_start_id} from tip at {self._user_start_id}")


    def run(self, signaling) -> dict:
        while signaling['running']:
            if self._current_id > (self._scan_start_id+ScanMachine.MAX_DISTANCE):
                self._current_id = self._scan_start_id
            if self._norm_online_peek(self._current_id):
                print("hit")
                # backtrack to the exact beginning of the new block
                while self._norm_online_peek(self._current_id - 1) == True:
                    if self._current_id <= self._scan_start_id:
                        break
                    self._current_id -= 1
                return {
                    'last_id' : self._current_id
                }
            self._current_id += ScanMachine.STEP
            sleep(1)

        return False


class LoadMachine(StateMachine):
    def __init__(self, state, norm_online_load, norm_db_save):
        StateMachine.__init__(self)
        self._current_id = state['last_id']        
        self.norm_online_load = norm_online_load
        self.norm_db_save = norm_db_save
        print(f"loader will start at {self._current_id}")

    def run(self, signaling):
        while signaling['running']:
            norm = self.norm_online_load(self._current_id)
            if norm != None:
                print(f"new norm:\n{norm['ext_id']}")
                self.norm_db_save(norm)
            else:
                return {
                    'last_id': self._current_id - 1
                }
            self._current_id += 1
            sleep(0.3)
        return False


# Helper to stop properly on process signals
def running_handler(signaling):
    def handler(signum, frame):
        print('Signal handler called with signal', signum)
        signaling['running'] = False
    return handler


def main():
    signaling = {
        'running': True,
    }
    signal.signal(signal.SIGINT, running_handler(signaling))

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )

    norm_meta = gconf("NORM_META")
    llm_task_meta = gconf("LLM_TASK_META")

    def norm_db_load(norm_id: int) -> dict:
        return file_db.read(str(norm_id), norm_meta)

    def norm_online_peek(norm_id: int) -> bool:
        return scan_bo_gob_ar_section_one(norm_id, norm_meta, peek=True)

    def norm_online_load(norm_id: int) -> bool:
        return scan_bo_gob_ar_section_one(norm_id, norm_meta, peek=False)

    def norm_db_save(norm: dict):
        file_db.write(norm)

    state = {
        'last_id': 325654
    }

    while signaling['running']:
        scanner = ScanMachine(state, norm_db_load, norm_online_peek)
        state = scanner.run(signaling)
        if state:
            loader = LoadMachine(state, norm_online_load, norm_db_save)
            state = loader.run(signaling)


if __name__ == '__main__':
    main()

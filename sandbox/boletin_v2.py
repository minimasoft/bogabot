#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025
# New BO scrapper that can see the future (tm)

import json
import requests
import sys

from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path
from requests.adapters import HTTPAdapter, Retry
from file_db import FileDB, FileDBMeta, FileDBRecord
from global_config import gconf
from llm_tasks import get_llm_task_map, NotEnoughData
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


def scan_bo_gob_ar_section_one(current_id, meta):
    session = bo_gob_ar_session()
    data_link =f"{bo_gob_ar_url()}/detalleAviso/primera/{current_id}/1" # Yes... I know. Did you know?

    norm = FileDBRecord(meta)

    print(f"scanning: {data_link}")

    with session.get(data_link) as response:
        soup = BeautifulSoup(response.text, 'html.parser')

        title_div = soup.find('div', {'id': 'tituloDetalleAviso'})
        if title_div is None:
            return None

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


def main():
    last_id = 323270 # helper
    if len(sys.argv) == 2:
        last_id = int(sys.argv[1])

    llm_task_map = get_llm_task_map()

    file_db = FileDB(
        gconf("FILEDB_PATH"),
        gconf("FILEDB_SALT"),
    )
    norm_meta = gconf("NORM_META")
    llm_task_meta = gconf("LLM_TASK_META")
    current_id = last_id 
    last_new_task = last_id -1
    running = True
    while running:
        # don't scan too far
        if (current_id - last_new_task) > 102:
            if last_new_task > last_id:
                print("my work here is done.")
                sys.exit(0)
            print("too far... sleep and restart.")
            current_id = last_id
            sleep(10) # don't hit it too hard
            continue
        # check if already loaded
        print(f"check: {current_id}")
        norm = file_db.read(str(current_id), norm_meta)
        if norm == {}:
            # scan
            print(f"scan: {current_id}")
            norm = scan_bo_gob_ar_section_one(current_id, norm_meta)
            if norm is not None:
                print(f"new norm:\n{norm['ext_id']}")
                last_new_task = current_id
                file_db.write(norm)
            else:
                current_id += 100
                continue
        if norm is not None:
            norm_map = llm_task_map['norm']
            for attr in norm_map.keys():
                try:
                    if attr not in norm:
                        if norm_map[attr].check(norm, norm_meta.d()):
                            llm_task = norm_map[attr].generate(norm, norm_meta.d())
                            file_db.write(llm_task)
                except NotEnoughData:
                    pass
        current_id = current_id + 1
        


if __name__ == '__main__':
    main()

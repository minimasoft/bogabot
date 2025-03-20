# Copyright Minimasoft (c) 2025
# New BO scrapper that can see the future (tm)
from bs4 import BeautifulSoup
from pathlib import Path
import json
import requests
from requests.adapters import HTTPAdapter, Retry
import sys

tasks_path = Path('../tasks_v2/')
tasks_path.mkdir(exist_ok=True)


def get_day(day:int ,month:int , year:int, last_id=0):
    session = requests.Session()
    retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        })
    session.get("https://www.boletinoficial.gob.ar/")
    fecha = f"{day:02}-{month:02}-{year}"
    session.get(f"https://www.boletinoficial.gob.ar/edicion/actualizar/{fecha}")
    found_page = True
    test_id=last_id
    while found_page:
        data_link =f"https://www.boletinoficial.gob.ar/detalleAviso/primera/{test_id}/20250319"
        print(data_link)
        with session.get(data_link) as r:
            html_content = r.text
            
        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        new_task = {}
        for title_div in soup.find_all('div', {'id': 'tituloDetalleAviso'}):
            print("something")
            new_task['subject'] = title_div.find('h1').text.strip()
            print(new_task['subject'])
            if title_div.find('h2'):
                new_task['name'] = title_div.find('h2').text.strip()
            else:
                new_task['name'] = ""

            new_task['order'] = test_id - last_id
            if title_div.find('h6'):
                more_data = title_div.find('h6').text.strip()
                new_task['official_id'] = more_data
            else:
                new_task['official_id'] = ""

            new_task['data_link'] = data_link

        if new_task == {}:
            break
        task_path = tasks_path / f"bo_{year}_{month:02}_{(day+1):02}_el_{test_id}.json"
        if task_path.exists() == False:
            with open(task_path, 'w', encoding='utf-8') as task_file:
                json.dump(new_task, task_file, indent=2, ensure_ascii=False)
        print(f"\n\n-- {new_task}")
        test_id += 1


# Get BO and generate metadata

day= int(sys.argv[1])
month= int(sys.argv[2])
year= int(sys.argv[3])
last_id = int(sys.argv[4])

get_day(day,month,year,last_id)

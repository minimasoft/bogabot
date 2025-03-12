# Copyright Minimasoft (c) 2025
from bs4 import BeautifulSoup
from pathlib import Path
import json
import requests
from requests.adapters import HTTPAdapter, Retry
import sys

tasks_path = Path('../tasks/')
tasks_path.mkdir(exist_ok=True)


def get_day(day:int ,month:int , year:int):
    session = requests.Session()
    retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        })
    session.get("https://www.boletinoficial.gob.ar/")
    fecha = f"{day:02}-{month:02}-{year}"
    session.get(f"https://www.boletinoficial.gob.ar/edicion/actualizar/{fecha}")
    with session.get("https://www.boletinoficial.gob.ar/seccion/primera") as r:
        html_content = r.text

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    results = {}
    order = 0
    # Find all div elements with class "col-md-12"
    for item_div in soup.find_all('div', {'class': 'col-md-12'}):
        # Extract the link from the anchor tag
        a_tag = item_div.find('a')
        if a_tag:
            link = a_tag['href']
        else:
            continue
        if link in results:
            continue

        # Extract subject from p with class "item"
        subject_p = item_div.find('p', class_='item')
        if subject_p:
            subject = subject_p.get_text(strip=True)
        else:
            continue

        # Extract name and official_id from the first two p.item-detalle
        detalle_ps = item_div.find_all('p', class_='item-detalle')
        name_small = detalle_ps[0].find('small') if detalle_ps else None
        name = name_small.get_text(strip=True) if name_small else ''

        if len(detalle_ps) > 1:
            official_id_small = detalle_ps[1].find('small')
            official_id = official_id_small.get_text(strip=True) if official_id_small else ''
        else:
            official_id = ''

        # Append the extracted data as a dictionary
        element = {
            'subject': subject,
            'order': order,
            'name': name,
            'official_id': official_id,
            'data_link': f"https://www.boletinoficial.gob.ar{link}",
        }
        task_path = tasks_path / f"bo_{year}_{month:02}_{day:02}_el_{link.split('/')[-2]}.json"
        if task_path.exists() == False:
            with open(task_path, 'w', encoding='utf-8') as task_file:
                json.dump(element, task_file, indent=2, ensure_ascii=False)
                order = order + 1
        print(f"\n\n-- subject: {subject} name: {name} id: {official_id}")


# Get BO and generate metadata
day= int(sys.argv[1])
month= int(sys.argv[2])
year= int(sys.argv[3])

get_day(day,month,year)

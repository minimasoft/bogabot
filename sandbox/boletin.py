# Copyright Minimasoft 2025
from bs4 import BeautifulSoup
from pathlib import Path
import json
import requests
from requests.adapters import HTTPAdapter, Retry
import markdown
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

        do_ref = True
        if len(official_id) < 1 or official_id[:2] in ["DI","RE"]:
            do_ref = False
        # Append the extracted data as a dictionary
        element = {
            'subject': subject,
            'link': link,
            'order': order,
            'name': name,
            'official_id': official_id,
            'data_link': f"https://www.boletinoficial.gob.ar{link}",
        }
        task_path = tasks_path / f"bo_{year}_{month:02}_{day:02}_el_{link.split('/')[-2]}.json"
        if task_path.exists() == False:
            with open(task_path, 'w', encoding='utf-8') as task_file:
                json.dump(element, task_file, indent=2, ensure_ascii=False)
            
        results[link] = element
        print(f"\n\n-- subject: {subject} name: {name} id: {official_id}")
    return results


# Get BO and generate metadata
day= int(sys.argv[1])
month= int(sys.argv[2])
year= int(sys.argv[3])

get_day(day,month,year)

sys.exit(0)
# Gen HTML

with open(f"bo{year-2000}{month:02}{day:02}.html",'w') as html_o:
    html_o.write("""<html>
<head>
<meta charset="UTF-8">
<style>
@font-face {
  font-family: 'Noto Sans Mono';
  font-style: normal;
  font-weight: 400;
  font-stretch: 100%;
  src: url(/NotoSansMonoLatin.woff2) format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}

body {
    font-family: 'Noto Sans Mono';
    font-size: 16px;
}

table {
  border: 1px solid black;
  border-collapse: collapse;
  width: 100%;
  max-width: 1000px;
}

td {
  border: 1px solid black;
  border-collapse: collapse;
  vertical-align: top;
  text-align: left;
  padding: 10px;
}

</style>
</head>
<body>
<a href=/><img src=bogabanner.png></img></a>
<h2>Agregado de la sección primera del bolet&iacute;n oficial fecha """)
    html_o.write(f"{day}/{month}/{year}</h2>")
    html_o.write("""
    <table>
    <tbody>""")
    for result in results.values():
        html_o.write(f"<tr>\n<td>\n")
        html_o.write(f"<details><summary><b>{result['subject']}  -  {result['official_id'] or result['name']}</b></summary><hr>via: <a href=https://www.boletinoficial.gob.ar{result['link']}>{result['link']}</a>\n")
        if 'brief' in result['data']:
            brief = result['data']['brief']
            brief = markdown.markdown(brief)        
            html_o.write(f"<p>{brief}</p>\n")
        if 'ref' in result['data']:
            ref = result['data']['ref']
            ref = markdown.markdown(ref)        
            html_o.write(f"<details><summary><b>Referencias</b></summary>{ref}</details>\n")
        if 'analysis' in result['data']:
            analysis = result['data']['analysis']
            analysis = markdown.markdown(analysis)        
            html_o.write(f"<details><summary><b>Análisis de bogabot</b></summary>{analysis}</details>\n")
        html_o.write(f"<details><summary><b>Texto original</b></summary>{result['data']['full_text']}</details>\n")
        html_o.write(f"</div></details>\n</td>\n</tr>\n")
    html_o.write('\n</tbody></table></body></html>\n')
